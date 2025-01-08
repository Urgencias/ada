
{ pkgs }: {
  deps = [
    pkgs.python3
    pkgs.poetry
    pkgs.postgresql
    pkgs.openssl
    pkgs.imagemagick
  ];
}
