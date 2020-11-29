let
  sources = import nix/sources.nix;
  pkgs = import sources.nixpkgs {};
  mach-nix = import sources.mach-nix {};
  py = mach-nix.mkPython {
    # replace with mkPythonShell if shell is wanted
    requirements = builtins.readFile ./requirements.txt;
  };
in

pkgs.mkShell {
  buildInputs = [
    py
    pkgs.jupyter
  ];
}
