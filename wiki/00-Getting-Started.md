# Getting started

---

## Installation:

### Use this Libary locally:

1. Clone the repo: `git clone -b lib https://git.zema.de/tfs/ZISS/_git/nope-py`
2. Install the depencies by typing `pip install .` or use `00-install.bat`

---

## Documentation

The Documentation is contained in here. Alternative you can create a Documentation using `./doc/install.bat html`. This will create the Documentation under `docs/build/html`.

You'll additional help under `wiki`.

The `wiki` is mostly running as `Markdown` or `Jupyter`-Notebook.

### Run the wiki

1. Install the documents via: `00-install-jupyter.bat`
   1. Install the `jupyter` with `pip3 install jupyter`
2. Run the `01-start-jupyter.bat`

---

## Contribute

To contribute to the Project, please perform the following steps:

0. Perform the Steps in `PREPARE_VSCODE.md`
1. Assign a new Version under `contribute/VERSION`
2. Fillout the Change Log in the `CHANGELOG.md`
3. Implement Your Changes and **Test-Cases**:

   1. For Testing the Library [`pytest`](https://docs.pytest.org) is used (click [here](https://docs.pytest.org) for more details).
   2. name your tests `test_*.py`
   3. run the tests with `python -m pytest`

4. If the Test are successfully proceed, otherwise perform your Bugfixes
5. Run the Code-Formater: `./02-format.bat`
6. Push the Code to the Git

---

### Commiting Changes

For simpler usage, you can use the following helpers:

- `00-install.bat`, which will compile the library for the browser and nodejs
- `10-push-to-npm.bat`, which will push the library to the pip registry.