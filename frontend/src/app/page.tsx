import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
      <main className="text-center">
        <h1 className="text-4xl font-extrabold text-gray-900 mb-4">
          Система складання розкладу занять
        </h1>
        <p className="text-lg text-gray-600 mb-8 max-w-2xl mx-auto">
          Автоматизація навчального процесу, генерація розкладів та управління навантаженням для навчальних закладів.
        </p>
        <Link
          href="/login"
          className="inline-block bg-blue-600 text-white font-medium px-8 py-3 rounded-md hover:bg-blue-700 transition shadow-sm"
        >
          Увійти в панель керування
        </Link>
      </main>
    </div>
  );
}