import { dur, rupiah, MODE_LABEL, dateID, timeWIB } from "@/lib/format";

const Row = ({ label, value, strong, testid }) => (
  <div className={`flex justify-between gap-4 py-1.5 border-b border-dashed last:border-0 ${strong ? "font-bold text-[#0B1F3A]" : ""}`}>
    <span className={strong ? "" : "text-muted-foreground"}>{label}</span><span className="mk-num" data-testid={testid}>{value}</span>
  </div>
);

export function PayrollBreakdown({ line }) {
  const d = line.durations;
  const c = line.counts;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 p-5 bg-[#F4F7FB]/70 text-sm" data-testid={`breakdown-${line.code}`}>
      <div className="mk-card p-4">
        <div className="mk-eyebrow mb-2">Durasi · {MODE_LABEL[line.payroll_mode]}</div>
        <Row label="Durasi aktual" value={dur(d.raw_minutes)} />
        <Row label="Durasi istirahat" value={dur(d.break_minutes)} />
        <Row label="Penyesuaian keterlambatan" value={dur(d.late_adjustment_minutes)} />
        <Row label="Durasi memenuhi syarat" value={dur(d.eligible_minutes)} />
        <Row label="Hasil pembulatan" value={dur(d.rounded_minutes)} />
        <Row label="Jam dibayar" value={dur(d.paid_minutes)} strong />
        <Row label="Jam lembur valid" value={dur(line.overtime_minutes)} />
        <div className="text-xs text-muted-foreground mt-2">Hadir {c.hadir} · Sakit {c.sakit} · Izin {c.izin} · Alfa {c.alfa} · Terlambat {c.late} · Jam pertama gugur {c.forfeited}{c.incomplete ? ` · ${c.incomplete} sesi belum Keluar (tidak dibayar)` : ""}</div>
      </div>
      <div className="mk-card p-4">
        <div className="mk-eyebrow mb-2">Penghasilan</div>
        {line.payroll_mode === "hourly" && <>
          <Row label={`Reguler ${rupiah(line.regular_rate)} × ${(d.paid_minutes / 60).toFixed(2)} jam`} value={rupiah(line.regular_amount)} />
          <Row label={`Lembur ${rupiah(line.overtime_rate)} × ${(line.overtime_minutes / 60).toFixed(2)} jam`} value={rupiah(line.overtime_amount)} />
        </>}
        {line.components.map((x, i) => <Row key={i} label={`${x.name} (${rupiah(x.amount)} × ${x.volume})`} value={rupiah(x.amount * x.volume)} />)}
        <Row label="Gaji kotor" value={rupiah(line.gross)} strong />
      </div>
      <div className="mk-card p-4">
        <div className="mk-eyebrow mb-2">Potongan</div>
        <Row label="Potongan lain" value={`− ${rupiah(line.other_deduction)}`} />
        <Row label="Bersih sebelum kasbon" value={rupiah(line.net_before_kasbon)} />
        <Row label="Saldo kasbon" value={rupiah(line.kasbon_balance)} />
        <Row label={`Potongan kasbon (maks ${rupiah(line.kasbon_cap)})`} value={`− ${rupiah(line.kasbon_deduction)}`} />
        <Row label="Sisa kasbon" value={rupiah(line.kasbon_after)} />
        <Row label="Gaji bersih akhir" value={rupiah(line.net_final)} strong />
      </div>
      {line.sessions.length > 0 && (
        <div className="lg:col-span-3 mk-card p-4 overflow-x-auto">
          <div className="mk-eyebrow mb-2">Rincian harian</div>
          <table className="w-full text-xs">
            <thead className="text-left text-muted-foreground"><tr><th className="py-1">Tanggal</th><th>Status</th><th>Masuk</th><th>Keluar</th><th>Aktual</th><th>Istirahat</th><th>Penyesuaian</th><th>Memenuhi syarat</th><th>Dibayar</th></tr></thead>
            <tbody>{line.sessions.map((s, i) => (
              <tr key={i} className="border-t">
                <td className="py-1">{dateID(s.date)}</td><td className="capitalize">{s.status}{s.is_late ? " · terlambat" : ""}{s.first_hour_forfeited ? " · jam pertama gugur" : ""}</td>
                <td className="mk-num">{timeWIB(s.check_in)}</td><td className="mk-num">{timeWIB(s.check_out)}</td>
                {s.status === "hadir" ? <>
                  <td className="mk-num">{dur(s.raw_minutes)}</td><td className="mk-num">{dur(s.break_minutes)}</td><td className="mk-num">{dur(s.late_adjustment_minutes)}</td>
                  <td className="mk-num">{dur(s.eligible_minutes)}</td><td className="mk-num font-semibold">{s.incomplete ? "belum Keluar" : dur(s.paid_minutes)}</td>
                </> : <td colSpan={5} className="text-muted-foreground">—</td>}
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}
