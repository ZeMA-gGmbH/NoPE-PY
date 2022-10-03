set DIR=%~dp0
cd "%DIR%"

rm ./dist
python setup.py bdist_wheel --universal