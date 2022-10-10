set DIR=%~dp0
cd "%DIR%"

autopep8 --in-place -r --aggressive ./nope
autopep8 --in-place -r --aggressive ./test