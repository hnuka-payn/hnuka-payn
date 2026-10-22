# 工夫の本棚

自己紹介と犬の散歩のイラストの下に、活動量を表す横長の本棚を表示します。

日別コントリビューションをUTCの直近12暦月にまとめ、左から順に12冊の本へ割り当てます。取得期間は11か月前の月初から取得時点までです。活動の多い月ほど本の高さと濃淡が増します。24秒のループで本が順番に少し浮き上がります。活動が0の月は低く淡い本になります。動き自体は装飾で、活動量に関係なく一定です。犬の紹介イラストと本文は活動データで変更しません。

取得するのは日付と日ごとの匿名集計だけです。会社名・組織名・リポジトリ名・PR名・コミット本文をクエリに含めず、出力にも含めません。公開画像には元の件数を埋め込まず、月ごとの高さ・濃淡へ変換します。

## private活動の接続

private活動を含めるには、本人のトークンで取得します。

1. 本人のclassic personal access tokenを `read:user` 権限だけで用意します。このクエリのために `repo` の権限を付ける必要はありません。
2. リポジトリのActions secret `PROFILE_READ_TOKEN` として設定します。トークン自体はソースへ書きません。
3. `Activity bookshelf` を手動実行します。以後は毎日00:17 JSTを目安に更新します。GitHub側の混雑によって実行が遅れる場合があります。

GitHubプロフィールの「Include private contributions on my profile」は、標準の活動グラフへ匿名の活動日・件数を公開する設定です。本棚への取得のために有効化する必要はありません。

`PROFILE_READ_TOKEN` がない場合は、公開分だけへ黙って切り替えずに停止します。APIエラー・不正なデータでも公開処理を止め、前回の画像を保持します。成功時は `output/profile.svg` が更新され、READMEがその画像を参照します。読み取り用トークンは取得ステップだけへ渡し、画像公開には組み込みの `GITHUB_TOKEN` を使います。APIの応答は一時ディレクトリだけへ保存し、画像以外を公開しません。

## ローカル確認

リポジトリのルートで実行します。入力JSONは `tools/calendar.graphql` の応答です。

```bash
python3 -m unittest discover -s tools -p 'test_*.py'
python3 tools/generate.py calendar.json dist/profile.svg
```

`assets/profile-template.svg` がデザインの原稿です。入力データで本棚の本だけを更新します。件数が数千になっても本は12冊のままで、大きさは対数で正規化します。動きを減らす設定では、犬と本棚のアニメーションを停止します。

## 公式仕様

[ContributionsCollectionとread:user](https://docs.github.com/en/graphql/reference/users#contributionscollection)、[private活動の匿名表示](https://docs.github.com/en/account-and-profile/how-tos/contribution-settings/manage-visibility-settings-for-private-contributions-and-achievements)。
