# PDChecker

PDChecker is an experimental static analysis tool for pandas based on alternative semantic.
PDChecker keeps tracks on column label/type of dataframes and provides type check information to user.
Also, PDChecker is in an early development stage currently, please feel free to play around.

## Usage

**Requirements**: Python 3.8

1. Download the source by `git clone`/github repo.

2. (Optional) preparing a virtual environment:

    ~~~~
    python3.8 -m venv venv
    source venv/bin/activate
    ~~~~

3. Install dependent packages:

    ~~~
    pip install -r requirements.txt
    ~~~

4. Check `pandas` codes by command-line or LSP:

    ~~~
    $ cd example; python ../checker.py ex.py
    4	2	Index 'not_existed' not found.
    ~~~


### LSP Server

`lsp.py` is a [Language Server][langserver] which fires a server instance up at `localhost:8080`。

[langserver]: https://microsoft.github.io/language-server-protocol/


## Overview

* `checker.py` is the interpreter which executes our checker's *semantic*.
* `spec.py` contains the definition of our checker's *check functions*.
* `lsp.py` is the LSP Server implementation.
