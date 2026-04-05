interface PlaceholderAppProps {
  appName: string
  jinjaPath: string
}

export default function PlaceholderApp({ appName, jinjaPath }: PlaceholderAppProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-gray-400">
      <p className="text-lg font-medium">{appName}</p>
      <p className="text-sm">Coming soon to the unified hub.</p>
      <a
        href={jinjaPath}
        className="text-sm text-blue-400 hover:text-blue-300 underline"
      >
        Open legacy {appName} page
      </a>
    </div>
  )
}
