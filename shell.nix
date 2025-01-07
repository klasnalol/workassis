{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  nativeBuildInputs = with pkgs.buildPackages; [
    python312
    python312Packages.python-lsp-server
  ];
  shellHook = ''
  '';  
}
