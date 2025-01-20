{ pkgs ? import <nixpkgs> {} }:
let ollamaDependencies = if builtins.pathExists ./ollama/dependencies.nix then (import ./ollama/dependencies.nix { inherit pkgs; }) else []; 
in
pkgs.mkShell {
  nativeBuildInputs = with pkgs.buildPackages; [
    python312
    python312Packages.python-lsp-server
  ] ++ ollamaDependencies;
  shellHook = ''
  '';  
}
