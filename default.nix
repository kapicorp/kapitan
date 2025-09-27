# from https://nixos.wiki/wiki/Python#Emulating_virtualenv_with_nix-shell
let
  pkgs = import <nixpkgs> { };
in
with pkgs;
pkgs.mkShell {
  buildInputs = [
    act
    gnumake
    kubernetes-helm
    libffi
    podman
    poetry
    ripgrep
    uv

    python312
    python312.pkgs.black
    python312.pkgs.cffi
    python312.pkgs.pip
    python312.pkgs.setuptools
  ];
  shellHook = ''
    # Tells pip to put packages into $PIP_PREFIX instead of the usual locations.
    # See https://pip.pypa.io/en/stable/user_guide/#environment-variables.
    export PIP_PREFIX=$(pwd)/_build/pip_packages
    export PYTHONPATH="$PIP_PREFIX/${python312.sitePackages}:$PYTHONPATH"
    export PATH="$PIP_PREFIX/bin:$PATH"
    unset SOURCE_DATE_EPOCH
  '';
}
