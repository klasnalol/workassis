{ pkgs ? import <nixpkgs> {} }:
let 
    ollamaDependencies = if builtins.pathExists ./ollama/dependencies.nix then (import ./ollama/dependencies.nix { inherit pkgs; }) else [];
    devDependencies = with pkgs.buildPackages; [ python312Packages.python-lsp-server gnum4 nodejs_22];
    pythonDependencies = with pkgs.buildPackages.python312Packages; [ sounddevice ];
in
pkgs.mkShell {
  nativeBuildInputs = with pkgs.buildPackages; [
    python312Full
    
    portaudio

  ] ++ pythonDependencies ++ devDependencies ++ ollamaDependencies;
  shellHook = ''
    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib
    . bin/activate
  '';  
}
