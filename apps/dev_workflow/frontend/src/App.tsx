export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <header className="h-12 border-b border-gray-800 flex items-center px-4">
        <span className="text-sm font-medium">Dev Workflow</span>
      </header>
      <main className="flex-1 flex">
        <div className="flex-1 p-4">Pipelines</div>
        <div className="w-64 border-l border-gray-800 p-4">Sessions</div>
      </main>
      <footer className="h-8 border-t border-gray-800 flex items-center px-4 text-xs text-gray-500">
        Status
      </footer>
    </div>
  )
}
