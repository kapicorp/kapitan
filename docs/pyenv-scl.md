# Kapitan on Older Linux Systems

## Introduction

Kapitan requires Python 3.6, and you need to be able to install the dependencies in the 
[requirements file](../requirements.txt).  However, sometimes this isn't entirely straightforward, and you may not be able or willing to install new versions of Python system-wide.  

We do provide a [dockerfile](../Dockerfile) which you can use to run Kapitan in a container, but if this isn't practical or possible either, you may wish to use one of the following options:
* [PyEnv](https://github.com/pyenv/pyenv) (Linux, distro-agnostic)
* [Software Collections](https://www.softwarecollections.org)(RHEL-based distros)

Both of these projects allow you to use a different version of Python specifically for your work with or on Kapitan.  They work similarly to [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html) but with more isolation from the lower-level OS-wide Python installation.  Both of these projects manipulate your shell environment variables to make sure you're using the right binaries and modules.  This document assumes you're using the bash shell. 

PyEnv and Software Collections are not Google projects, so please exercise your judgment as to whether these projects are suitable for your circumstances.

## On Debian-based Operating Systems - PyEnv

Here at Streams, we use a Debian-based operating system for our day-to-day work.  We've found that [PyEnv](https://github.com/pyenv/pyenv) works well for us.
### Getting Started
Take a look at the [PyEnv](https://github.com/pyenv/pyenv) project on Github.  There are two options for installing this project.  The author makes a separate installer script available at [this Github link](https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer), or you can manually install it.  We recommend using the automated installer unless you have reason to use the manual installation process.

### The Automated Installer

To use the installer, we would recommend downloading the installer script and examining it before you execute it. 
```console
$ curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer > pyenv-installer
```
Then, once you've checked it, you can execute it.  PyEnv doesn't need root privileges, so you can run it without using sudo
```console
$ bash ./pyenv-installer
```
Instructions on updating and removing the tool when you've installed it with the installer can be found on the pyenv-installer project page.  Pay attention to the output of the installer.  It might require you to add lines to your .bashrc file manually.

### Manually Installing from Github
Take a look at the README.md on the PyEnv project page and follow the installation instructions there.

### Using Kapitan with PyEnv
Once you have successfully installed PyEnv, you'll need to restart your shell.  Either open a new shell session or source your .bashrc file like so: 
```$ source ~/.bashrc```

Now that you have PyEnv ready to go, we can check it runs:
```console
$ pyenv 
pyenv 1.2.8
Usage: pyenv <command> [<args>]
...
```
Before you move onto the next step, you'll need to install some dependencies if they aren't already present.  To do this, you might need root access:
```console
# apt install libssl-dev libffi-dev
```

Let's install Python 3.7.1, which is a stable and up-to-date release at the time of writing.  We know Kapitan works with this release.
```console
$ pyenv install 3.7.1
Downloading Python-3.7.1.tar.xz...
-> https://www.python.org/ftp/python/3.7.1/Python-3.7.1.tar.xz
Installing Python-3.7.1...
Installed Python-3.7.1 to /home/mikejo/.pyenv/versions/3.7.1
$ pyenv local 3.7.1
$ python --version
Python 3.7.1
$ 
```
Once it completes, we can activate the newer Python installation and set about installing Kapitan!
Make sure PyEnv is activated using the ```$ pyenv local 3.7.1``` command above and then run the following:
```console
$ pip install --user --upgrade kapitan
```
After Kapitan is installed in this way, you might have to add the following to your PATH environment variable:
```console
${HOME}/.local/bin
```
and you can do this like so:
```console
export PATH=${HOME}/.local/bin:${PATH}
```
Add that line to the end of your .bashrc if you'd like it to take effect in all the shell sessions you use.
You can now check everything installed correctly and start using Kapitan!
```console
$ kapitan
usage: kapitan [-h] [--version] {eval,compile,inventory,searchvar,secrets} ...
```
## On RHEL-based Operating Systems - Software Collections
PyEnv will work on RHEL-based operating systems (including the upstream Fedora project).  Another option is to use the [Software Collections](https://www.softwarecollections.org/) project.  It's a community project with backing from Red Hat, and it includes both official Red Hat releases of some software collections and third-party contributions.  While Kapitan only needs you to install an official Red Hat collection release, please remember this isn't a Google project and to use your judgment as to whether this is appropriate for your circumstances.

### Installing Software Collections support on your machine

Software Collections has installation documentation available [here](https://www.softwarecollections.org/en/docs/)

As this procedure needs you to add a repository to the OS package manager, you'll need to be root.  Use ```su``` or run the following with ```sudo``` as appropriate.

Once you've completed the installation of the scl tool, install the Python 3.5 SCL package (YUM/DNF package names are identical to the name of the Software Collection).  
```console
# yum install rh-python35
```
As of this point, you don't need to be root any more.  Return to your regular shell and activate the Python 3.5 software collection you just installed.  This command starts a shell that uses the Python 3.5 installation you just carried out:
```console
$ scl enable rh-python35 bash
```
Install Kapitan:
```console
$ pip install --user --upgrade kapitan
```
After Kapitan is installed in this way, you might have to add the following to your PATH environment variable:
```console
${HOME}/.local/bin
```
and you can do this like so:
```console
export PATH=${HOME}/.local/bin:${PATH}
```
Add that line to the end of your .bashrc if you'd like it to take effect in all the shell sessions you use.
You can now check everything installed correctly and start using Kapitan!
```console
$ kapitan
usage: kapitan [-h] [--version] {eval,compile,inventory,searchvar,secrets} ...
```
When you come back to using this method after restarting your shell, you can switch back to the rh-python35 collection either by creating a shell alias for the kapitan command to ``` 'scl enable rh-python35 kapitan'``` 
but we recommend that you can use the scl command to start a new shell using
``` '$ scl enable rh-python35 bash' ```
Once you finish using the software collection, exit the shell with ``` exit ```  or ``` Ctrl+D ```

