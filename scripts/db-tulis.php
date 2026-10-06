<?php
// db-tulis.php — tulis/baca broker_summary. stdin JSON, stdout JSON.
//   echo '{"op":"init"}' | php db-tulis.php
//   echo '{"op":"put","rows":[...]}' | php db-tulis.php
//   echo '{"op":"get","kode":"ADRO","tgl_awal":"2026-09-03","tgl_akhir":"2026-10-03"}' | php db-tulis.php
//   php db-tulis.php --selftest
const DDL = "CREATE TABLE IF NOT EXISTS broker_summary (id BIGINT AUTO_INCREMENT PRIMARY KEY, kode VARCHAR(8) NOT NULL, tgl_awal DATE NOT NULL, tgl_akhir DATE NOT NULL, broker VARCHAR(4) NOT NULL, sisi ENUM('B','S') NOT NULL, lot BIGINT NOT NULL DEFAULT 0, val_rp BIGINT NOT NULL DEFAULT 0, avg INT NOT NULL DEFAULT 0, diambil DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY uq (kode, tgl_awal, tgl_akhir, broker, sisi), KEY ix (kode, tgl_akhir)) ENGINE=InnoDB";
function db() {
    $pdo = new PDO("mysql:host=" . (getenv("DB_HOST") ?: "127.0.0.1") . ";port=" . (getenv("DB_PORT") ?: "3306") . ";dbname=" . (getenv("DB_NAME") ?: "saham") . ";charset=utf8mb4", getenv("DB_USER") ?: "root", getenv("DB_PASS") ?: "");
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    return $pdo;
}
function out($a) { echo json_encode($a, JSON_UNESCAPED_UNICODE); exit(0); }
function fail($m) { echo json_encode(["ok" => false, "error" => $m], JSON_UNESCAPED_UNICODE); exit(1); }
if (in_array("--selftest", $argv ?? [])) {
    try {
        $pdo = db();
        $pdo->exec(DDL);
        $pdo->exec("DELETE FROM broker_summary WHERE kode='__TST__'");
        $st = $pdo->prepare("INSERT INTO broker_summary (kode,tgl_awal,tgl_akhir,broker,sisi,lot,val_rp,avg) VALUES ('__TST__','2026-01-01','2026-01-02','XX','B',10,20000,2000) ON DUPLICATE KEY UPDATE lot=VALUES(lot)");
        $st->execute();
        $n = $pdo->query("SELECT COUNT(*) FROM broker_summary WHERE kode='__TST__'")->fetchColumn();
        $pdo->exec("DELETE FROM broker_summary WHERE kode='__TST__'");
        out(["ok" => $n == 1, "selftest" => "rows=$n"]);
    } catch (Throwable $e) { fail($e->getMessage()); }
}
try {
    $in = json_decode(stream_get_contents(STDIN), true) ?? [];
    $pdo = db();
    if (($in["op"] ?? "") === "init") { $pdo->exec(DDL); out(["ok" => true]); }
    if (($in["op"] ?? "") === "put") {
        $pdo->exec(DDL);
        $st = $pdo->prepare("INSERT INTO broker_summary (kode,tgl_awal,tgl_akhir,broker,sisi,lot,val_rp,avg) VALUES (?,?,?,?,?,?,?,?) ON DUPLICATE KEY UPDATE lot=VALUES(lot),val_rp=VALUES(val_rp),avg=VALUES(avg)");
        $n = 0;
        foreach (($in["rows"] ?? []) as $r) { $st->execute([$r["kode"], $r["tgl_awal"], $r["tgl_akhir"], $r["broker"], $r["sisi"], (int)$r["lot"], (int)$r["val"], (int)$r["avg"]]); $n++; }
        out(["ok" => true, "rows" => $n]);
    }
    if (($in["op"] ?? "") === "get") {
        $st = $pdo->prepare("SELECT broker,sisi,lot,val_rp AS val,avg FROM broker_summary WHERE kode=? AND tgl_awal=? AND tgl_akhir=?");
        $st->execute([$in["kode"], $in["tgl_awal"], $in["tgl_akhir"]]);
        out(["ok" => true, "rows" => $st->fetchAll(PDO::FETCH_ASSOC)]);
    }
    fail("op tidak dikenal");
} catch (Throwable $e) { fail($e->getMessage()); }
