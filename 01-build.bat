set DIR=%~dp0
cd "%DIR%"

del ./dist
python setup.py bdist_wheel --universal