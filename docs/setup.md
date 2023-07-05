_elkplot_ manages its dependencies using [Poetry](https://python-poetry.org). If your project also uses poetry, all you need to do is the following:

```commandline
poetry add git+https://github.com/ejkaplan/elkplot
```

If you are using any other virtual environment manager (venv, conda, etc.) the following should work just fine:

```commandline
pip install "git+https://github.com/ejkaplan/elkplot"
```

You can verify that it worked by calling the following in your terminal...

```commandline
elk --help
```

and if you see the CLI reference pop up you'll know you're good to go!