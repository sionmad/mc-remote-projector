# xperiment

## 今何をしているのか？

pygame と minecraft-remote-api を使って、ゲーム画面や画像を Minecraft のブロックアートとして表示する仕組みを作っています。

***

## このプロジェクトの目標

pygame で作成したゲームウィンドウの画面をピクセル単位で変換し、minecraft-remote-api を使って Minecraft の中に表示するエンジンを作ることです。

***

## 使い方

### まずはデモを実行する

```bash
python main.py
```

このデモでは pygame のウィンドウを描画し、その内容を RGB ピクセルとして取得して、プレビュー表示します。`capture_window_pixels(...)` や `posterize(...)` をそのまま使えば、独自の pygame ループからも同じ処理を再利用できます。

### pygame 画面を Minecraft に送る

```bash
python main.py --minecraft
```

必要なら `--reset-world` を付けると、表示領域周辺をクリアできます。既定の縮小サイズは 64 x 36 です。

### 既存の pygame ファイルをそのままキャプチャする

```bash
python main.py --dot --minecraft path/to/your_game.py
```

`--dot` を使うと、対象の pygame スクリプトを変更せずに実行し、`pygame.display.flip()` や `pygame.display.update()` が呼ばれるたびに画面をキャプチャできます。

### 画像ファイルを Minecraft に送る

```bash
python main.py --image path/to/image.png --minecraft
```

PNG や JPG などの画像を読み込んで、その内容を Minecraft のブロック画面として表示できます。

### ブロックパレットを切り替える

```bash
python main.py --image path/to/image.png --minecraft --palette mixed
```

`--palette` では `concrete`、`wool`、`terracotta`、`mixed` を選べます。`mixed` ではコンクリートだけでなく、いくつかの自然ブロックや鉱石も候補に入ります。

## param_mc_remote を使った Minecraft 接続

Minecraft へ送信する経路では、プロジェクトルートの `param_mc_remote.py` と `axis_flat.py` を使います。
`--minecraft` を実行する前に、これらのモジュールが import できる状態で、`param_mc_remote.py` に Minecraft サーバーの接続情報が設定されていることを確認してください。

よくある準備事項:

- `param_mc_remote.py` でサーバーのアドレスやポートを設定する
- プレイヤー名や初期座標が自分のワールドに合っているか確認する
- プロジェクトルートから実行して、ローカルモジュールが正しく解決されるようにする

例:

```bash
python main.py --minecraft
```

表示領域を先に空にしたい場合は、`--reset-world` を付けます。

***