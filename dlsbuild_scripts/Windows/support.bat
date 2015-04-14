:: ****************************************************************************
:: 
:: Script to build a Diamond production module.in the support or ioc areas
::
:: This is a partial script which builds a module in for the dls-release
:: system. The script is prepended with a list of variables before invocation
:: by the dls-release mechanism. These variables are:
::
::   _email     : The email address of the user who initiated the build
::   _epics     : The DLS_EPICS_RELEASE to use
::   _build_dir : The parent directory in the file system in which to build the
::                module. This does not include module or version directories.
::   _svn_dir or _git_dir : The directory in subversion where the module is
::                          located.
::   _module    : The module name
::   _version   : The module version
::   _area      : The build area
::   _force     : Force the build (i.e. rebuild even if already exists)
::   _build_name: The base name to use for log files etc.
::

setlocal enabledelayedexpansion enableextensions

:: Set up environment
set DLS_EPICS_RELEASE=%_epics%
call W:\etc\profile.bat
echo on
if errorlevel 1 call :ReportFailure %ERRORLEVEL% Could not find profile. Aborting build.
set SVN_ROOT=http://serv0002.cs.diamond.ac.uk/repos/controls

set "build_dir=%_build_dir:/=\%\%_module%"

:: Checkout module
mkdir "%build_dir%"
if errorlevel 1 call :ReportFailure %ERRORLEVEL% Can not mkdir %build_dir%

cd /d "%build_dir%"
if errorlevel 1 call :ReportFailure %ERRORLEVEL% Can not cd to %build_dir%

if not defined _svn_dir (
  if not exist %_version% (
    git clone --depth=100 %_git_dir% %_version%
    if errorlevel 1 call :ReportFailure %ERRORLEVEL% Can not clone  %_git_dir%
    pushd %_version% && git checkout %_version% && popd
    if errorlevel 1 call :ReportFailure %ERRORLEVEL% Can not checkout %_version%
  ) else if "%_force%"=="true" (
    rmdir /s/q %_version%
    if errorlevel 1 call :ReportFailure %ERRORLEVEL% Can not remove %_version%
    git clone --depth=100 %_git_dir% %_version%
    if errorlevel 1 call :ReportFailure %ERRORLEVEL% Can not clone  %_git_dir%
    pushd %_version% && git checkout %_version% && popd
    if errorlevel 1 call :ReportFailure %ERRORLEVEL% Can not checkout %_version%
  ) else (
    pushd %_version% && git fetch --tags && git checkout %_version% && popd
    if errorlevel 1 call :ReportFailure %ERRORLEVEL% Directory %build_dir%/%_version% not up to date with %_git_dir%
  )
) else if not defined _git_dir (
  if not exist %_version% (
      svn checkout %_svn_dir% %_version%
      if errorlevel 1 call :ReportFailure %ERRORLEVEL% Can not check out %_svn_dir%
  ) else if "%_force%"=="true" (
      rmdir /s/q %_version%
      if errorlevel 1 call :ReportFailure %ERRORLEVEL% Can not remove %_version%
      svn checkout %_svn_dir% %_version%
      if errorlevel 1 call :ReportFailure %ERRORLEVEL% Can not check out %_svn_dir%
  ) else (
      For /f "tokens=1 delims=:" %%G in ('svn status') Do (set _line=%%G)
      if not "%_line%"=="Status against revision" call :ReportFailure 1 Directory %build_dir%/%_version% not up to date with %_svn_dir%
  )
) else (
  call :ReportFailure 1 both _git_dir and _svn_dir are defined; unclear which to use
)
cd "%_version%"
if errorlevel 1 call :ReportFailure %ERRORLEVEL% Can not cd to %_version%

:: Modify configure\RELEASE
if not defined _svn_dir (
  git cat-file -p HEAD:configure/RELEASE > configure\RELEASE.vcs
) else (
  svn cat configure\RELEASE > configure\RELEASE.vcs
)

del configure\RELEASE
for /f "delims=" %%i in ( configure\RELEASE.vcs ) do (
   set TMP_LINE=%%i
   set TMP_LINE=!TMP_LINE: =!

   if "!TMP_LINE:~0,5!"=="WORK=" (
       echo # WORK=commented out to prevent prod modules depending on work modules>> configure\RELEASE
   ) else (
       echo %%i>> configure\RELEASE
   )
)

echo EPICS_BASE=%EPICS_BASE:\=/%>  configure\RELEASE.%EPICS_HOST_ARCH%
echo SUPPORT=W:/prod/%_epics:_64=%/support>> configure\RELEASE.%EPICS_HOST_ARCH%

copy configure\RELEASE.%EPICS_HOST_ARCH% configure\RELEASE.%EPICS_HOST_ARCH%.Common

:: Build
set error_log=%_build_name%.err
set build_log=%_build_name%.log

%_make% clean
:: make
%_make% 1>%build_log% 2>%error_log%
set make_status=%ERRORLEVEL%
echo %make_status% > %_build_name%.sta
if NOT "%make_status%"=="0" call :ReportFailure %make_status% Build Errors for %_module% %_version%

goto :EOF

:ReportFailure
    if exist "%build_dir%/%_version%" echo %1 > "%build_dir%\%_version%\%_build_name%.sta"
    echo #### ERROR [%DATE% %TIME%] ### Error code: %*
    exit /B %1
    goto :EOF
