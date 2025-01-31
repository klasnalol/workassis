{ pkgs ? (import (fetchTarball https://channels.nixos.org/nixpkgs-unstable/nixexprs.tar.xz)) {} }:
let
    ollamaDependenciesPath = ./modules/ollama/dependencies.nix;
    ollamaDependencies = if builtins.pathExists ollamaDependenciesPath then (import ollamaDependenciesPath { inherit pkgs; }) else [];
    devDependencies = with pkgs.buildPackages; [ python312Packages.python-lsp-server ffmpeg  gnum4 nodejs_22 ];
    pythonDependencies = with pkgs.buildPackages.python312Packages; [ sounddevice ];
in
pkgs.mkShell {
  nativeBuildInputs = with pkgs.buildPackages; [
    python312Full
    
    portaudio

  ] ++ pythonDependencies ++ devDependencies ++ ollamaDependencies;
  shellHook = ''
    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib
  '';  
}
