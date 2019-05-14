# standalone kapitan executable
Create a portable (i.e. static) kapitan binary for users. This executable will be made available for each release on Github. The target/tested platform is Debian 9 (possibly Windows to be supported in the future).

Criteria:
- speed of the resulting binary
- size of the resulting binary
- portability of the binary (single-file executable or has an accompanying folder)
- cross-platform
- actively maintained
- supports Python 3.6, 3.7

Author: @yoshi-1224

### Tools to be explored
- (tentative first-choice) [Pyinstaller](https://github.com/pyinstaller/pyinstaller) 
- (Alternative) [nuitka](https://github.com/Nuitka/Nuitka) (also part of GSoC 2019. It might soon support [single-file executable output](https://github.com/Nuitka/Nuitka/issues/230)). 