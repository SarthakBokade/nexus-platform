{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.mupdf
    pkgs.freetype
    pkgs.libjpeg
    pkgs.zlib
  ];
}
