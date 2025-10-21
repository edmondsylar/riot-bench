# TickTalk Python (TTPython)

MIT License

[TTPython Docs](http://ccsg.ece.cmu.edu/ttpython/overview.html)

[Mailing List](mailto:ticktalk-python@lists.andrew.cmu.edu)

## Installation

TTPython runs in Python 3, and has been tested on Python >=3.8.  We recommend
using a virtual environment manager like
[Conda](https://www.anaconda.com/products/individual) or
[python virtual environments](https://docs.python.org/3/tutorial/venv.html)

Clone the TTPython repository to your local directory

```
git clone https://bitbucket.org/ccsg-res/ticktalkpython.git
```

Install the dependencies for TTPython

```
pip install -r requirements.txt
```

If you wish to use the graphviz package for graph visualization during
compilation (when calling compile, setting use_graphviz=True), then that package
must be installed with a few extra steps. The package "graphviz" will be
installed by pip, but a corollary (and necessary) package
[pygraphviz](https://pygraphviz.github.io/) requires a few additional steps.
On Mac, we find 'brew' to be the best avenue for the initial build process,
which requires more than just pip or conda installations.

## Basic Testing and Verification

In the top level of the repo, there is a jupyter notebook that will compile
and simulate a simple TTPython example to help get you started. This is helpful
for verifying the installation process worked correctly.

```
jupyter notebook TickTalkTest.ipynb
```


Open the Jupyter notebook and run the first two blocks within the notebook.

The first will run a set of basic regression tests and compile a TTPython program
in the 'examples' directory called ```streaming_merge```. This program simply
produces two streams of values representing sinusoids sampled every 500 ms, and
adds them together. It also computes a moving average on one of the sinusoid
streams.

The second block in the notebook will interpret the graph within a simulated
environment. Note that this may be quite slow within jupyter, taking up to 40
seconds to finish (running from terminal is about 2 orders of magnitude faster).
If it finishes correctly, it will produce two output graphs depicting the added
sinusoids and the moving average.

FAQ:

```
Can I run TTPython in Google Colab environment?
```
Unfortunately, Colab uses python version 3.7 as default. We recomment a virtual
environment only above 3.8.

```
Why am I get 'No module named' error while running the TickTalkTest.ipynb notebook?
```
Make sure that all the requirements in the requirements.txt file are installed.
If you are using a conda environment, you may want to recheck the python base version.

Also note that while using a conda environment, the ast_scope package requires pip
since conda package is not available.
```
pip install ast_scope
```

Additionally, graphviz requires two additional 'python-graphviz' and 'pydot' as well
if you are using conda.
```
conda install python-graphviz
conda install pydot
```

## Documentation

You can compile a local version of the docs in the ```docs/``` folder.
You will need ```sphinx``` installed to compile the docs.
Run ```make html``` to generate static html pages found in the ```build/```
subdirectory.
If you have pdfTex, you can generate a pdf with ```make latexpdf```.
