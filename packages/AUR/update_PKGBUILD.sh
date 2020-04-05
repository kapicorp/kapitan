VERSION=$(cat kapitan/version.py | sed -n "/VERSION = /s/VERSION = //p" | tr -d "'")
DESCRIPTION=$(cat kapitan/version.py | sed -n "/DESCRIPTION = /s/DESCRIPTION = //p" | tr -d '"')
MD5Hash=$(curl -sL https://github.com/deepmind/kapitan/archive/v${VERSION}.tar.gz | md5sum  | cut -d ' ' -f 1)

sed -i "s/pkgver=.*/pkgver=$VERSION/g" ./packages/AUR/PKGBUILD
sed -i "s/pkgdesc=.*/pkgdesc='$DESCRIPTION'/g" ./packages/AUR/PKGBUILD
sed -i "s/md5sums=.*/md5sums=('$MD5Hash')/g" ./packages/AUR/PKGBUILD