# updates INDEX

- [2026-08-23.md](2026-08-23.md) — レギュレータ過電流時の自動リセット機能追加(mada_regulator_autoreset.py新規、mada.py/mada_set_ap.py/config skeleton改修)
- [2026-08-24.md](2026-08-24.md) — .madaファイル欠損時にRunLoggerが例外終了する不具合を修正(mada.py)
- [2026-08-27.md](2026-08-27.md) — ボードセットアップがperiodごとに再実行される不具合を修正(mada.py、DAQ開始時1回のみに変更)
- [2026-08-28.md](2026-08-28.md) — mada.pyにバックグラウンド実行機能を追加(mada_daemon.py/mada_stop_daq.py新規、-d/--daemon・-l/--log・-p/--pidfile追加)
- [2026-08-28_2.md](2026-08-28_2.md) — SIGKILL時にMadaIwakiの書き込みバッファが未flushでデータ欠落する不具合を修正(MadaIwaki.cc)
- [2026-09-07.md](2026-09-07.md) — rateログのフォーマット不整合を修正(mada_rate_log.py新規、mada.py/mada_daq_killer.py/mada_log_data_size.pyを共通フォーマットに統一)
- [2026-10-10.md](2026-10-10.md) — LVリセット監視をmada.pyから独立した常駐プロセスにし、vetoの操作を監視プロセスに一本化(APがOFFの基板は対象外、release失敗時の再試行と安全停止)
- [2026-10-14.md](2026-10-14.md) — LVリセット監視の起動をrun_set_ap(io=1)で保証(mada.py/encoder_power/set_ap共通)、全基板AP OFFが続くと自動終了、排他ロックで二重起動防止
- [2026-10-14_2.md](2026-10-14_2.md) — DAQ enableを終了検知の直後にlatch downし、LOWの間にMadaIwaki起動・カウンタリセットしてからlatch upする手順へ変更(先頭の古いイベントとカウンタの飛びを解消)
- [2026-10-14_3.md](2026-10-14_3.md) — ADALMのDIO書き込みをバッファで同時書き込みに変更(counter reset等の複数ピンの立ち上がり・立ち下がり時間差約4msを解消、パルス幅もサンプル単位に)
