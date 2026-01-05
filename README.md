


# 仮想環境を作る
python -m venv .venv

# 有効化
.venv\Scripts\Activate.ps1

# 必要なライブラリを入れる
python -m pip install --upgrade pip
pip install pandas numpy scikit-learn jupyter ipykernel matplotlib


# メモ
目的：
・何を予測 / 知りたいか

データ概要：
・行数：
・列数：
・価格列（あれば）：

第一印象：
・欠損が多そう
・列が多い
・日付あり

