## Installation
### Ubuntu Linux WSL Install
1. Install WSL  
    → `wsl --install`

2. Reboot  

3. Sign in and create your Ubuntu Account  
    → `wsl`

4. Update Ubuntu  
    → `sudo apt update && sudo apt upgrade -y`

5. Download the FreeCAD `.AppImage` from the [FreeCAD website](https://www.freecad.org/downloads.php)  

6. Extract the app image using  
    → `/path/to/FreeCAD.AppImage --appimage-extract`

7. Rename the extracted app image directory:  
    → `mv ./squashfs-root/ ./FreeCAD/`

8. Remove the `.AppImage` file  
    → `rm /path/to/FreeCAD.AppImage`

9.  Test run FreeCAD (should be no problems)  
    → `./FreeCAD/AppRun`

10. Install Git-LFS  
    → `sudo apt install git-lfs`

11. fork and clone the repo  
    → *Note: Copy the ssh link instead of the https link on GitHUB under the green clone button.*

12. Run the init repo script for GitCAD twice (specify the FreeCAD python file in the config file after the first run), as per the install instructions in the [README](README.md).  
    → `./FreeCAD_Automation/user_scripts/init-repo`

13. Get a FreeCAD `.FCStd` file to test xdg-open on later  
    → `git checkout test_binaries -- ./FreeCAD_Automation/tests/AssemblyExample.FCStd`

14. install xdg-open (used to open `.FCStd` files via CLI)  
    → `sudo apt install xdg-utils desktop-file-utils shared-mime-info`

15. Configure xdg-open to work for FreeCAD using a `.desktop` file and MIME  `.xml` type file  
    1.  Create a `freecad.xml` MIME type file in `/usr/share/mime/packages/freecad.xml`  
        ```xml
        <?xml version="1.0" encoding="UTF-8"?>
        <mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
            <mime-type type="application/x-freecad">
                <comment>FreeCAD Document</comment>
                <glob pattern="*.FCStd"/>
            </mime-type>
        </mime-info>
        ```
    2. Create a `freecad.desktop` file in `/usr/share/applications/freecad.desktop`
        ```desktop
        [Desktop Entry]
        Type=Application
        Name=FreeCAD
        GenericName=3D CAD Modeler
        Comment=Parametric 3D CAD Modeler
        Exec=/path/to/FreeCAD/AppRun %F
        Icon=/path/to/FreeCAD/freecad.png
        Terminal=false
        Categories=Engineering;Science;
        MimeType=application/x-freecad;
        StartupWMClass=FreeCAD
        StartupNotify=true
        ```
    3. Validate the `.desktop` file (if nothing is printed, everything is good)  
        → `desktop-file-validate /usr/share/applications/freecad.desktop` 
    4. Update MIME types  
        → `sudo update-mime-database /usr/share/mime`
    5. Update desktop databases  
        → `sudo update-desktop-database`
    6. Try opening the `AssemblyExample.FCStd` file  
        → `xdg-open ./FreeCAD_Automation/tests/AssemblyExample.FCStd`

16. Setup ssh for git credentials → Ask Google or ChatGPT  

17. Run `./FreeCAD_Automation/tests/run_repo_tests.sh --sandbox`  
    1.  When the terminal says `>>>> START SANDBOX TEST? <<<<` press ENTER
    2.  If the terminal says:  
        - `>>>>>> Sandbox Setup, Press ENTER when done testing to exit and reset to main.....`  
        - And you can run `xdg-open ./FreeCAD_Automation/tests/AssemblyExample.FCStd` in another terminal to open the file in FreeCAD  
    3.  Then everything is setup correctly.

### Windows Install
1.  Download the FreeCAD from the [FreeCAD website](https://www.freecad.org/downloads.php)

2.  install [Git-LFS](https://git-lfs.com) if needed  

3.  fork and clone the repo  

4.  Run the init repo script for GitCAD twice (and specify the FreeCAD python file in the config), as per the install instructions in the [README](README.md) file.  
    → `./FreeCAD_Automation/user_scripts/init-repo`

5.  Run `./FreeCAD_Automation/tests/run_repo_tests.sh --sandbox`
    1.  When the terminal says `>>>> START SANDBOX TEST? <<<<` press ENTER
    2.  If the terminal says:  
        - `>>>>>> Sandbox Setup, Press ENTER when done testing to exit and reset to main.....`  
        - And you can run `start ./FreeCAD_Automation/tests/AssemblyExample.FCStd` in another terminal to open the file in FreeCAD  
    3.  Then everything is setup correctly.

## How to contribute
1.  Fork the repository.

2.  Create a feature branch

3.  Implement your contribution

4.  Test your changes:
    - If modifying the `/FreeCAD_Automation/FCStdFileTool.py`:
        - Run and complete all the python tests in `/FreeCAD_Automation/tests/run_python_test.sh`
    - If modifying one of the bash `.sh` scripts:
        - Run and complete `/FreeCAD_Automation/tests/run_repo_tests.sh`

5.  Push your changes to your fork

6.  Submit and create a Pull Request to merge your feature branch into GitCAD.

## Standards
-   Timestamps should all match *ISO 8601 extended format with offset from UTC* IE: `2025-12-29T01:24:31.998058+00:00`. To compare timestamps use lexical comparisons (NOT numerical).
    -   Python: `import datetime; print(datetime.datetime.now(datetime.timezone.utc).isoformat())`
        -   Comparison: `if t1 < t2:`
    
    -   Bash: `echo "$(date -u +"%Y-%m-%dT%H:%M:%S.%6N%:z")"`
        -   Comparison: `if [[ "$t1" < "$t2" ]]; then`  
            *Note: Must use [[ ]]. Single brackets don't work.*