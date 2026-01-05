# FreeCAD Git Automation
**Video Demo:** https://youtu.be/wSL3G5QyPD0  
**Video Tutorial:** https://youtu.be/oCrGdhwICGk  
## Description
This repository contains tools and scripts to automate the git workflow for committing uncompressed `.FCStd` files. Binary/other non-human-unreadable files such as `.brp` files are stored using git LFS (optionally they are compressed before storing them as LFS objects). Also supports locking `.FCStd` files to enable multi file collaboration.

### Key Features
- **Git Clean Filter**: Tricks git into thinking `.FCStd` files are empty and exports `git fadd`(ed) (( `fadd` is a git alias )) `.FCStd` files to their uncompressed directories.
  
- **Various Hooks**: Imports uncompressed data into `.FCStd` to keep them synced when git commands cause changes to uncompressed data (the uncompressed data is what is stored in git, not the `.FCStd` file itself).  
Sets `.FCStd` files to readonly if not locked by the user. Prevents user from committing / pushing changes for `.FCStd` files (and their uncompressed data) that the user doesn't own the lock for.
  
- **Locking Mechanism**: Users use the git aliases `git lock path/to/file.FCStd` and `git unlock path/to/file.FCStd` lock a `.lockfile` inside the uncompressed data directory instead of the `.FCStd` file itself.  
   NOTE: THE COMMAND IS **NOT** `git lfs lock`/`git lfs unlock`
   - Why lock `.lockfile` instead of `.FCStd` directly?  
      *`.FCStd` files are filtered to appear empty to git to save space.  
      If the `.FCStd` files were directly locked you would be storing the entire `.FCStd` file in git-lfs,  
      which would somewhat defeat one of the secondary purposes of extracting the `.FCStd` files in the first place...  
      To efficiently store the diffable contents separate from the binary contents.*

### Alternative Solutions to GitCAD (SVN)
Another viable solution is to use svn (subversion) instead of git. Subversion natively supports locking files (no need to use git LFS). Subversion also has a nice GUI solution (TortoiseSVN) that will graphically show a lock icon on files that are locked.

With subversion you will basically be storing the entire `.FCStd` file instead of its uncompressed data directly.

For diffing I'm sure you can do something similar to:
```
git config diff.zip.textconv "unzip -c -a"
echo "*.ARCHIVE_EXTENSION diff=zip" >> .gitattributes
```
To tell svn that it can simply extract the zipped files contents to get some text data that can be compared.

[Here is a demo of TortoiseSVN locking](https://www.youtube.com/watch?v=7TPpwFhEAJA).

## Installation
**Video:** https://youtu.be/t5OylIiA-A0  
1. Dependencies
   - [Git](https://git-scm.com)
   - [Git-LFS](https://git-lfs.com)

2. Ensure `FreeCAD > Tools > Edit Parameters > Preferences > Document` has a boolean key `BackupPolicy` set to `false`.  
   - Techically only required if `require-lock-to-modify-FreeCAD-files` is configured to `true`.  
   - If the boolean key does not exist, create it.  
   - This prevents FreeCAD overwritting readonly (locked) files.  
   - Git is your new backup policy lol  

3. Download and extract the latest release into the root of your FreeCAD project's git repository.

4. Run the initialization script:
   *Note: Linux users will need to make the script executable with `chmod`*
   ```bash
   ./FreeCAD_Automation/user_scripts/init-repo
   ```

5. Configure the settings in newly added `FreeCAD_Automation/config.json` (from initialization script) as needed.  
   *Note 1: When you re-run the initialization script later in this installation guide this file will be added to `.gitignore` automatically.*  
   *Note 2: For documentation on what every json item does see the [Configuration Options](#configuration-options) section.*
   
   **Make sure to configure:**
    - `freecad-python-instance-path` -- Path to FreeCAD's Python executable.  
      *IE WINDOWS: `C:/Path/To/FreeCAD 1.0/bin/python.exe`*  
      -- **NOTE: MUST BE `/`, NOT `\`**  
      
      *IE LINUX: `/path/to/FreeCAD_Extracted_AppImage/usr/bin/python`*  
      -- **NOTE: LINUX USERS WILL NEED TO `FreeCAD.AppImage --appimage-extract`**  

6. Run the initialization script one last time:
   ```bash
   ./FreeCAD_Automation/user_scripts/init-repo
   ```
   *The Script can be ran multiple times without error (assuming the config wasn't changed).*  
   To see how to change `x` configuration post initialization see the [Changing Things](#changing-things) section.

7. Test your configurations:
    - To see how your `.FCStd` files will export use:  
      `git fexport path/to/file.FCStd`  
      *Note: User will need to delete exported contents if they want to try a different `uncompressed-directory-structure` or `compress-non-human-readable-FreeCAD-files` config setting*  
      *See the [Changing Things](#changing-things) section for details on modifying the config file post-initialization.*

8. Modify the default config file in the `Create Config File` section of the `init-repo` script to match your changes to `FreeCAD_Automation/config.json`.  
   *Note: This is for future users and you if you clone the repository elsewhere.*
   - Assuming everyone has a different install directory for FreeCAD, you can leave `freecad-python-instance-path` empty as is.

9. Update your `.gitattributes` with LFS files you want to track.  
   - `git lfs track "*.zip"` -- This is done automatically by the `init-repo` script.  
   __The following is recommended if `compress-non-human-readable-FreeCAD-files` is disabled in config:__
     - `git lfs track "**/no_extension/*"` -- folder created by this script to track files without extension
     - `git lfs track "*.brp"` -- FreeCAD binary file, stores the 3D shape data of an object
     - `git lfs track "*.Map.*"` -- FreeCAD text files that contain a bunch of numbers that aren't really human readable.
     - `git lfs track "*.png"` -- thumbnail pictures

10. Verify `.gitattributes` is tracking files you want to track:  
   `git check-attr --all /path/to/file/to/check`

11. Update your `README.md` documentation for collaboration.  
   *Template available in [Template.md](template.md).*

## Updating
**Video:** https://youtu.be/qhY4L0984Lg  
1. Backup/make note of:  
   - The *default* `config.json` defined in `FreeCAD_Automation/user_scripts/init-repo`  
   - Your `freecad-python-instance-path` in `FreeCAD_Automation/config.json`.

2. Delete `FreeCAD_Automation/config.json`

3. Download and extract the latest release into the root of your FreeCAD project's git repository.

4. Manually merge (if required) your backup of the `config.json` into the new (updated?) default `FreeCAD_Automation/config.json` defined in `FreeCAD_Automation/user_scripts/init-repo`.

5. Run the initialization script:
   ```bash
   ./FreeCAD_Automation/user_scripts/init-repo
   ```
   *This will re-create an updated `FreeCAD_Automation/config.json` file.*  
   *The Script can be ran multiple times without error (Assuming config wasn't changed).*
   To see how to change `x` configuration post initialization see the [Changing Things](#changing-things) section.

6. Paste your saved `freecad-python-instance-path` back into the newly re-created `FreeCAD_Automation/config.json`

## [Git Aliases](FreeCAD_Automation/docs/added-aliases.md)
**Video Demo:** https://youtu.be/wSL3G5QyPD0  
**Video Tutorial:** https://youtu.be/oCrGdhwICGk  
### DESCRIPTION
It is important to read the linked alias documentation (click the heading). These aliases help ensure the `.FCStd` files in your working directory are correctly synced with their corresponding uncompressed directories.

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

### If you forgot to use one of the above commands instead:
1. Use `git fimport path/to/file.FCStd` to manually import the uncompressed data to its `.FCStd` file.
2. Use `git fcmod path/to/file.FCStd` to make git think your `.FCStd` file is empty (clears the modification in git's view assuming an empty `.FCStd` has already been committed).

## Changing Things
Some configurations in `FreeCAD_Automation/config.json` cannot be changed by simply changing its value in the JSON file. After you have already initialized the repository with the `init-repo` script.

This section will cover how you can change certain configurations, post-initialization.

If not mentioned here, you can just assume that changing the configuration value in the JSON is all that is required.

### Changing `uncompressed-directory-structure`
If you change any value inside the `uncompressed-directory-structure` JSON key, you will need to follow this checklist to properly propagate that configuration change to your repository.
- [ ] `git lock --force "*.FCStd"` to get edit permissions.  
      *Note 1: Only necessary if the user has already committed the uncompressed directory to git*  
      *Note 2: The `"` surrounding the `*.FCStd` are important, without it your shell might expand it to just the files in the root directory, instead of ALL the `.FCStd` files in the repository.*  

- [ ] `git mv path/to/unchanged/dir path/to/changed/dir` all uncompressed FCStd file folders to move them from their old location to the new location specified in the updated `uncompressed-directory-structure` JSON key.

- [ ] Ensure `git status` shows directories as `renamed`, **NOT** `deleted` and `added`.  
      *Note: Only necessary if the user has already committed the uncompressed directory to git*

- [ ] Change the values of the `uncompressed-directory-structure` JSON key to match.

- [ ] `git commit` & `git push` changes.
      *Note: Only necessary if the user has already committed the uncompressed directory or config file to git*

- [ ] `git unlock "*.FCStd"` to get edit permissions.  
      *Note 1: Only necessary if the user has already committed the uncompressed directory to git*
      *Note 2: The `"` surrounding the `*.FCStd` are important, without it your shell might expand it to just the files in the root directory, instead of ALL the `.FCStd` files in the repository.*  

## Configuration Options
```jsonc
{
    // Location of the python interpreter bundled with your FreeCAD installation.
    // Linux users may need to unpack their app image of FreeCAD to get access to this.
    // NOTE: Make sure to use `/` instead of `\` (( probably, I haven't tested TBH ))
    "freecad-python-instance-path": "C:/path/to/FreeCAD 1.0/bin/python.exe",

    // ------------------------------------------------------------------
    
    // If true, Post-Checkout will set all FreeCAD files to readonly 
    // (unless you have the lock for that file)
    
    // TL;DR: It simulates the --lockable git lfs attribute.

    // If you change this post-initialization, 
    // make sure to re-run the `init-repo` script.
    "require-lock-to-modify-FreeCAD-files": true,

    // ------------------------------------------------------------------
    
    // If true, most* (not all, notably `git checkout`) git operations will fail unless you activate the GitCAD environment
      // PowerShell Activation Command: .\FreeCAD_Automation\user_scripts\activate.ps1
      //       Bash Activation Command: source FreeCAD_Automation/user_scripts/activate
    "require-GitCAD-activation": true,

    // ------------------------------------------------------------------
    
    // If true, thumbnails will be exported and imported to/from the .FCStd file.
    "include-thumbnails": true,

    // ------------------------------------------------------------------
    
    // Configures the name and location of the uncompressed .FCStd file directory.

    // Current config exports .FCStd file to:
    //      /path/to/file.FCStd -> /path/to/compressed/FCStd_file_FCStd/

    // To change this post initialization follow instructions in `## Changing Things`
    "uncompressed-directory-structure": {
        "uncompressed-directory-suffix": "_FCStd",
        "uncompressed-directory-prefix": "FCStd_",
        "subdirectory": {
            "put-uncompressed-directory-in-subdirectory": true,
            "subdirectory-name": "uncompressed"
        }
    },
            
    // ------------------------------------------------------------------
                
    "compress-non-human-readable-FreeCAD-files": {
        // If enabled, after exporting the .FCStd file to a directory,
        // files/folders with names matching strings listed
        // will be further compressed to save git LFS space.

        // Using template patterns and compression level 9 reduces FreeCAD BIMExample.FCStd's
        // created folder by 67.98%.

        // Enabling this option makes exporting .FCStd files take considerably longer on max compression level.
        // If too unbearable and you don't mind a reduced compression, reduce the compression-level property below.
        "enabled": true,
        
        // --------------------------------------------------------------
            
        // File/folder names to match
        // Note 1: "*/no_extension" is a directory all files without extension are added to. 
        //         This is for convenience of being able to use git LFS to track specifically files without extension.
        
        // Note 2: Pattern matching uses PurePosixPath().match(). See documentation here: https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.match
        //         FreeCAD's python is version Python 3.11.13 FYI (hence not using full_match())

        // Note 3: My template pattern matching is also compressing certain text files. This is because they are written in a way that only
        //         a computer / algorithm could understand. Diffing them has no value in my opinion.
        //         Basically the only thing left uncompressed with this template is Document.xml and GuiDocument.xml.
        "files-to-compress": ["**/no_extension/*", "*.brp", "**/thumbnails/*", "*.Map.*", "*.Table.*"],
        
        // --------------------------------------------------------------
        
        // Max size of compressed archive.
        // If value is exceeded an additional zip file will be created.
        
        // See the following for GitHub's LFS limitations:
            // https://docs.github.com/en/billing/concepts/product-billing/git-lfs#free-use-of-git-lfs
            // https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage#about-git-large-file-storage
        "max-compressed-file-size-gigabyte": 2,
        
        // --------------------------------------------------------------

        // level of compression 0-9
        // zlib documentation: https://docs.python.org/3/library/zlib.html#zlib.compress
        "compression-level": 9,
        
        // --------------------------------------------------------------

        // Prefix for created zip files.
        // IE: Current setting will create `compressed_binaries_{i}.zip` where {i} is an iterator for all created zip files (that exceed `max-compressed-file-size-gigabyte`).
        "zip-file-prefix": "compressed_binaries_"
    }
}
```