import BikeSearch from "../components/BikeSearch";

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <header className="max-w-4xl mx-auto px-6 mb-12">
        <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight">
          VeloGraph
        </h1>
        <p className="text-lg text-gray-600 mt-2">
          Explore and compare bicycle frame geometries.
        </p>
      </header>

      <main>
        <BikeSearch />
      </main>

      <footer className="max-w-4xl mx-auto px-6 mt-20 pt-8 border-t border-gray-200 text-center text-gray-400 text-sm">
        <p>© 2025 VeloGraph. Powered by FastAPI & Next.js.</p>
      </footer>
    </div>
  );
}
