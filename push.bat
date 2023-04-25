@RD /S /Q  %~dp0\dist
@RD /S /Q  %~dp0\build

python setup.py sdist
twine upload dist/* --verbose