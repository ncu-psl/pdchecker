# PDChecker

PDChecker 是一個實驗性的針對 `pandas` 的靜態分析工具，
用於追蹤 `DataFrame`, `Series` 的欄位與型別資訊進行型別檢查工作。
目前還在極度早期的開發階段，為概念實作等級。

## Usage

**環境要求**: Python 3.8

在這個初步階段，可以透過下列步驟來實驗此工具

1. 透過 `git clone` 或是下載的方始取得原始碼
2. （可選）使用 Virtual Environment 來準備環境

    ~~~~
    pip -m venv venv
    source venv/bin/activate
    ~~~~
3. 安裝相依套件

    ~~~
    pip install -r requirements.txt
    ~~~

4. 使用指令列或是LSP來檢查 `pandas` 程式碼

    ~~~
    $ cd example; python ../checker.py ex.py
    4	2	Index 'not_existed' not found.
    ~~~


### LSP Server

`lsp.py` 是一個 [Language Server][langserver]，執行後會在 `localhost:8080`。

[langserver]: https://microsoft.github.io/language-server-protocol/


## Overview

* `checker.py` 為檢查語意的直譯器
* `spec.py` 為檢查語意中函數的定義
* `lsp.py` 為 LSP Server 的實作

