call ./venv/Scripts/activate

pip install twine

python setup.py sdist

twine upload dist/*
