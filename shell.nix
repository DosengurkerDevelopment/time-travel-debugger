let
  sources = import nix/sources.nix;
  pkgs = import sources.nixpkgs {};
  unstable = import sources.unstable {};
  mach-nix = import sources.mach-nix {};
  py = mach-nix.mkPython {
    # replace with mkPythonShell if shell is wanted
    requirements = builtins.readFile ./requirements.txt;
  };
  jupyter = import sources.jupyterWith {};
  iPython = jupyter.kernels.iPythonWith {
    name = "python";
    packages = p: with p; [ numpy ];
  };
  jupyterEnvironment =
    jupyter.jupyterlabWith {
      kernels = [ iPython ];
      extraPackages = _: [
        unstable.python37Packages.ipython
        unstable.python37Packages.lxml
        unstable.python37Packages.cssselect
        unstable.python37Packages.colorama
        unstable.python37Packages.ipywidgets
        unstable.python37Packages.ipykernel
        unstable.python37Packages.widgetsnbextension
      ];
    };
in

pkgs.mkShell {
  buildInputs = [
    py
    unstable.python37Packages.ipython
    unstable.python37Packages.lxml
    unstable.python37Packages.cssselect
    unstable.python37Packages.colorama
    unstable.python37Packages.ipywidgets
    unstable.python37Packages.ipykernel
    unstable.python37Packages.widgetsnbextension
    jupyterEnvironment
  ];
}
