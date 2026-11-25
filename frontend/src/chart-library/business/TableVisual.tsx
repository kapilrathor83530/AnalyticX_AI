interface Props {
  data: Record<string, unknown>[]
  title?: string
}

export default function TableVisual({ data, title }: Props) {
  if (!data.length) return <div className="p-4 text-sm text-slate-500">No rows</div>

  const columns = Object.keys(data[0])

  return (
    <div className="flex h-full flex-col p-3">
      {title && <h3 className="mb-2 text-sm font-semibold text-slate-200">{title}</h3>}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr className="border-b border-slate-800">
              {columns.map((col) => (
                <th key={col} className="py-2 pr-4">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 200).map((row, i) => (
              <tr key={i} className="border-b border-slate-800/60">
                {columns.map((col) => (
                  <td key={col} className="py-1 pr-4 text-slate-300">
                    {String(row[col] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
