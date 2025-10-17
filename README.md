図書管理システム

これは、小規模な図書室向けのシンプルな図書管理システムです。Webアプリケーションとして実装されており、図書の登録、利用者登録、貸出、返却の基本機能を提供します。

主な機能

図書登録: 新しい図書（タイトル、著者、ISBN）をデータベースに登録します。

利用者登録: 新しい利用者（氏名、メールアドレス）をデータベースに登録します。

図書一覧表示: 登録されているすべての図書を本棚形式で表示します。貸出状況も確認できます。

貸出処理: 利用者と貸し出す図書を選択し、貸出記録を作成します。

返却処理: 貸出中の図書を返却状態に更新します。

貸出履歴: すべての貸出・返却記録を一覧で確認できます。

使用技術

バックエンド: Python, Flask

フロントエンド: HTML, Tailwind CSS, JavaScript

データベース: SQLite

セットアップと実行方法

リポジトリをクローン:

git clone <リポジトリのURL>
cd Homework2


仮想環境の作成と有効化:

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate


必要なライブラリをインストール:

pip install -r requirements.txt


Flaskアプリケーションの実行:

flask run


アプリケーションを実行すると、library.dbという名前のデータベースファイルが自動的に作成されます。

ブラウザでアクセス:
Webブラウザを開き、 http://127.0.0.1:5000 にアクセスしてください。

Renderへのデプロイ

このアプリケーションは、PaaSであるRenderに簡単にデプロイできます。

GitHubにリポジトリをプッシュ: このプロジェクトを自身のGitHubアカウントにプッシュします。

Renderにサインアップ: Renderにアクセスし、GitHubアカウントでサインアップします。

新しいWeb Serviceを作成:

Renderのダッシュボードで「New +」→「Web Service」を選択します。

デプロイしたいGitHubリポジトリを選択して接続します。

Name: サービス名（例: library-system）

Root Directory: （空欄のままでOK）

Environment: Python 3

Build Command: pip install -r requirements.txt

Start Command: gunicorn app:app (※本番環境ではgunicornの利用を推奨します)

gunicornをrequirements.txtに追加:
デプロイする前に、requirements.txtにgunicornを追加してください。

Flask
Flask-SQLAlchemy
gunicorn


「Create Web Service」をクリック: デプロイが自動的に開始されます。完了すると、公開URLが発行されます。