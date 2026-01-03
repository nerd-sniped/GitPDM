## GitCAD
This repository contains tools and scripts to automate the git workflow for committing `.FCStd` files in their uncompressed form (GitCAD is the name of the collection of tools and scripts). The complete documentation for these tools and scripts can be found on the [Official GitCAD repository](https://github.com/MikeOpsGit/GitCAD).

### Setting Up This Repository
**Video:** https://youtu.be/uZSZUam3BbI  
1. Dependencies
   - [Git](https://git-scm.com)
   - [Git-LFS](https://git-lfs.com)

2. Ensure `FreeCAD > Tools > Edit Parameters > Preferences > Document` has a boolean key `BackupPolicy` set to `false`.  
   - Techically only required if `require-lock-to-modify-FreeCAD-files` is configured to `true`.  
   - If the boolean key does not exist, create it.  
   - This prevents FreeCAD overwritting readonly (locked) files.  

3. Clone the the repository.

4. Run the initialization script:
   *Note: Linux users will need to make the script executable with `chmod`*
   ```bash
   ./FreeCAD_Automation/user_scripts/init-repo
   ```
   *This will create a `FreeCAD_Automation/config.json` file.*
   
5. Configure the settings in newly added `FreeCAD_Automation/config.json` (from initialization script) as needed.  
   
   **Make sure to configure:**
    - `freecad-python-instance-path` -- Path to FreeCAD's Python executable.  
      *IE WINDOWS: `C:/Path/To/FreeCAD 1.0/bin/python.exe`*  
      -- **NOTE: MUST BE `/`, NOT `\`**  
      
      *IE LINUX: `/path/to/FreeCAD_Extracted_AppImage/usr/bin/python`*  
      -- **NOTE: LINUX USERS WILL NEED TO `FreeCAD.AppImage --appimage-extract`**  

6. Run the initialization script one last time to complete the initialization:
   ```bash
   ./FreeCAD_Automation/user_scripts/init-repo
   ```
   *The Script can be ran multiple times without error.*  
   *When the script asks "Do you want to import data from all uncompressed FreeCAD dirs?" in the "Synchronizing \`.FCStd\` Files" section, press `y`*

### If The GitCAD Plugin For This Repository Updates:
**Video:** https://youtu.be/h9ZnDH6Oc8Q  
1. Backup/make note of your `freecad-python-instance-path` in `FreeCAD_Automation/config.json`.

2. Delete `FreeCAD_Automation/config.json`
   
3. Run the initialization script:
   ```bash
   ./FreeCAD_Automation/user_scripts/init-repo
   ```
   *This will re-create an updated `FreeCAD_Automation/config.json` file.*  
   *The Script can be ran multiple times without error (Assuming config wasn't changed).*
   
4. Paste your saved `freecad-python-instance-path` back into the newly re-created `FreeCAD_Automation/config.json`

### Git Aliases
**Video Demo:** https://youtu.be/wSL3G5QyPD0  
**Video Tutorial:** https://youtu.be/oCrGdhwICGk  
#### DESCRIPTION
GitCAD adds some unique aliases to manage `.FCStd` files in accordance with git. Full documentation for all of these files can be found in the [added-aliases.md](FreeCAD_Automation/docs/added-aliases.md) file.

These aliases help ensure the `.FCStd` files in your working directory are correctly synced with their corresponding uncompressed directories.

They are also important for manually resynchronizing them in case you forgot to use an alias.

For examples see the [examples.md](FreeCAD_Automation/docs/examples.md) file.

### IMPORTANT ALIASES / TL;DR:
*Note: See the [GitCAD Activation Section](FreeCAD_Automation/docs/added-aliases.md#gitcad-activation) for more information on with/without GitCAD Activation means.*

#### With GitCAD Activation
1. `git lock path/to/file.FCStd` / `git unlock path/to/file.FCStd` / `git locks` -- Do what you expect

#### Without GitCAD Activation
1. Use `git fadd` instead of `git add` to export `.FCStd` files.
2. Use `git freset` instead of `git reset`
3. Use `git fstash` instead of `git stash`
4. Use `git fco COMMIT FILE [FILE ...]` instead of `git checkout COMMIT -- FILE [FILE ...]`  
5. `git lock path/to/file.FCStd` / `git unlock path/to/file.FCStd` / `git locks` -- Do what you expect

#### If you forgot to use one of the above commands instead:
1. Use `git fimport` to manually import the contents of a dir to its `.FCStd` file.
2. Use `git fcmod` to make git think your `.FCStd` file is empty (clears the modification in git's view assuming an empty `.FCStd` has already been committed).