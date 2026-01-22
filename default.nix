# from https://nixos.wiki/wiki/Python#Emulating_virtualenv_with_nix-shell
let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  buildInputs = [
    pkgs.act
    pkgs.gnumake
    pkgs.kubernetes-helm
    pkgs.libffi
    pkgs.podman
    pkgs.poetry
    pkgs.ripgrep
    pkgs.uv

    pkgs.python312
    pkgs.python312.pkgs.black
    pkgs.python312.pkgs.cffi
    pkgs.python312.pkgs.pip
    pkgs.python312.pkgs.setuptools
  ];
  shellHook = ''
    # Tells pip to put packages into $PIP_PREFIX instead of the usual locations.
    # See https://pip.pypa.io/en/stable/user_guide/#environment-variables.
    export PIP_PREFIX=$(pwd)/_build/pip_packages
    export PYTHONPATH="$PIP_PREFIX/${pkgs.python312.sitePackages}:$PYTHONPATH"
    export PATH="$PIP_PREFIX/bin:$PATH"
    unset SOURCE_DATE_EPOCH
  '';
}
