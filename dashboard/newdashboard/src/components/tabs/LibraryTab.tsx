import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../lib/api';
import { Book, BookDetail, BookChapter, ROOM_IDS, ROOM_LABELS, RoomId } from '../../types';
import { SectionHeading, EmptyState, SkeletonBlock } from '../ui/DashboardPrimitives';
import { Modal } from '../ui/Modal';
import { cn } from '../../lib/utils';
import {
  BookOpen, Upload, Play, Pause, Square, Trash2, Search, ChevronRight,
  Music, FileText, Check, Clock, Loader2, PlayCircle, BookMarked
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export function LibraryTab() {
  const [books, setBooks] = useState<Book[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [selectedBook, setSelectedBook] = useState<BookDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [selectedRoomId, setSelectedRoomId] = useState<string>(ROOM_IDS.LIVING);
  const [isDeleting, setIsDeleting] = useState<number | null>(null);
  const [voices, setVoices] = useState<{id: string, name: string}[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    fetchBooks();
    api.getVoices().then(res => setVoices(res.voices)).catch(console.error);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchBooks(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const fetchBooks = async (q?: string) => {
    try {
      if (!q) setIsLoading(true);
      const data = await api.getBooks(q);
      setBooks(data);
    } catch (e) {
      console.error('Failed to fetch books', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBookClick = async (id: number) => {
    setIsLoadingDetail(true);
    setSelectedBook(null);
    try {
      const detail = await api.getBook(id);
      setSelectedBook(detail);
    } catch (e) {
      console.error('Failed to fetch book details', e);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      await api.uploadBook(file);
      await fetchBooks(searchQuery);
    } catch (error) {
      console.error('Failed to upload book', error);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Tem certeza que deseja excluir este livro?')) return;
    setIsDeleting(id);
    try {
      await api.deleteBook(id);
      if (selectedBook?.id === id) {
        setSelectedBook(null);
      }
      await fetchBooks(searchQuery);
    } catch (e) {
      console.error('Failed to delete book', e);
    } finally {
      setIsDeleting(null);
    }
  };

  const handlePlay = (chapterIndex?: number) => {
    if (!selectedBook) return;
    try {
      const idx = chapterIndex ?? 0;
      
      // Notify backend (fire-and-forget for 'local' since GET /audio handles the actual generation wait)
      api.playBook(selectedBook.id, selectedRoomId, idx).catch(e => console.error('Play API error', e));

      if (selectedRoomId === 'local' && audioRef.current) {
        // Set src instantly and play to preserve the user's click gesture.
        // The backend GET /audio endpoint will block until the MP3 is ready!
        audioRef.current.src = `/api/library/books/${selectedBook.id}/chapters/${idx}/audio`;
        audioRef.current.play().catch(e => console.error('Audio play blocked:', e));
      }
    } catch (e) {
      console.error('Failed to play book', e);
    }
  };

  const handlePause = async () => {
    if (!selectedBook) return;
    if (selectedRoomId === 'local' && audioRef.current) {
      audioRef.current.pause();
      return;
    }
    try {
      await api.pauseBook(selectedBook.id, selectedRoomId);
    } catch (e) {
      console.error('Failed to pause book', e);
    }
  };

  const handleResume = async () => {
    if (!selectedBook) return;
    if (selectedRoomId === 'local' && audioRef.current) {
      audioRef.current.play().catch(e => console.error('Audio play blocked:', e));
      return;
    }
    try {
      await api.resumeBook(selectedBook.id, selectedRoomId);
    } catch (e) {
      console.error('Failed to resume book', e);
    }
  };

  const handleVoiceChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (!selectedBook) return;
    const newVoice = e.target.value;
    // Optimistic update
    setSelectedBook({ ...selectedBook, voice_name: newVoice });
    try {
      await api.updateBookVoice(selectedBook.id, newVoice);
    } catch (err) {
      console.error('Failed to update voice', err);
    }
  };

  return (
    <div className="flex h-full flex-col gap-6 overflow-y-auto pb-10 pr-2">
      <audio ref={audioRef} className="hidden" controls={false} />
      {/* Header Zone */}
      <div className="alfredo-card relative overflow-hidden p-5 md:p-6">
        <div className="absolute right-0 top-0 h-64 w-64 translate-x-1/3 -translate-y-1/3 rounded-full bg-brass-500/10 blur-[80px]" />
        
        <div className="relative z-10">
          <SectionHeading
            eyebrow="ALFREDO READS"
            title="Biblioteca"
            subtitle="Livros e leitura interativa com efeitos sonoros"
          />
          
          <div className="mt-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="relative w-full max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--text-tertiary)]" />
              <input
                type="text"
                placeholder="Buscar livros..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="alfredo-input w-full pl-10"
              />
            </div>
            
            <div className="relative">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleUpload}
                accept=".epub,.pdf"
                className="hidden"
                id="book-upload"
              />
              <label
                htmlFor="book-upload"
                className={cn(
                  'flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-brass-500/30 bg-brass-500/5 px-6 py-3 transition-all hover:bg-brass-500/10',
                  isUploading ? 'pointer-events-none opacity-50' : ''
                )}
              >
                {isUploading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-brass-400" />
                ) : (
                  <Upload className="h-5 w-5 text-brass-400" />
                )}
                <span className="text-[13px] font-medium text-brass-300">
                  {isUploading ? 'Enviando...' : 'Fazer upload de EPUB/PDF'}
                </span>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Grid Zone */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="alfredo-card flex flex-col gap-3 p-5">
              <SkeletonBlock className="h-4 w-3/4" />
              <SkeletonBlock className="h-3 w-1/2" />
              <div className="mt-4 flex gap-2">
                <SkeletonBlock className="h-5 w-12 rounded-full" />
                <SkeletonBlock className="h-5 w-16 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      ) : books.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          tone="brass"
          title={searchQuery ? 'Nenhum livro encontrado' : 'Sua biblioteca está vazia'}
          description={
            searchQuery
              ? 'Tente buscar com outros termos.'
              : 'Faça upload do seu primeiro livro (EPUB ou PDF) para iniciar a experiência de leitura interativa.'
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <AnimatePresence>
            {books.map((book) => (
              <motion.div
                key={book.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                layout
                onClick={() => handleBookClick(book.id)}
                className="alfredo-card group relative flex cursor-pointer flex-col overflow-hidden p-5 transition-all hover:scale-[1.02] hover:border-brass-500/30 hover:bg-white/[0.04] hover:shadow-[0_8px_32px_rgba(212,162,78,0.1)]"
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  <div className="flex flex-col">
                    <h3 className="line-clamp-2 text-[15px] font-semibold text-[color:var(--text-primary)] group-hover:text-brass-300 transition-colors">
                      {book.title}
                    </h3>
                    {book.author && (
                      <p className="line-clamp-1 mt-1 text-[12px] text-[color:var(--text-secondary)]">
                        {book.author}
                      </p>
                    )}
                  </div>
                  <div className="shrink-0 rounded-full bg-black/40 p-1.5 opacity-0 transition-opacity group-hover:opacity-100">
                    <ChevronRight className="h-4 w-4 text-brass-400" />
                  </div>
                </div>

                <div className="mt-auto pt-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="alfredo-pill border-white/10 bg-white/[0.03] text-[10px] font-medium uppercase tracking-wider text-[color:var(--text-secondary)]">
                      {book.format}
                    </span>
                    <span className="flex items-center gap-1 text-[11px] text-[color:var(--text-tertiary)]">
                      <FileText className="h-3 w-3" />
                      {book.total_chapters} cap.
                    </span>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Book Detail Modal */}
      <Modal open={!!selectedBook || isLoadingDetail} onClose={() => setSelectedBook(null)} title={selectedBook?.title || 'Carregando...'} maxWidth="max-w-4xl">
        {isLoadingDetail && !selectedBook ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-brass-400" />
            <p className="mt-4 text-[13px] text-[color:var(--text-secondary)]">Carregando detalhes do livro...</p>
          </div>
        ) : selectedBook ? (
          <div className="flex flex-col gap-6 md:flex-row">
            {/* Sidebar with controls */}
            <div className="flex w-full flex-col gap-5 md:w-64 shrink-0 border-r border-white/5 md:pr-5">
              <div className="flex flex-col gap-1 text-[13px] text-[color:var(--text-secondary)]">
                <p><strong>Autor:</strong> {selectedBook.author || 'Desconhecido'}</p>
                <p><strong>Adicionado:</strong> {new Date(selectedBook.added_at).toLocaleDateString('pt-BR')}</p>
                <p><strong>Formato:</strong> {selectedBook.format.toUpperCase()}</p>
              </div>

              <div className="h-px w-full bg-white/5" />

              <div className="flex flex-col gap-3">
                <label className="text-[12px] font-medium text-[color:var(--text-secondary)]">Tocar em...</label>
                <select
                  value={selectedRoomId}
                  onChange={(e) => setSelectedRoomId(e.target.value)}
                  className="alfredo-input w-full cursor-pointer py-2 text-[13px]"
                >
                  <option value="local">Neste Dispositivo (Navegador)</option>
                  {Object.entries(ROOM_LABELS).map(([id, label]) => (
                    <option key={id} value={id}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-[12px] font-medium text-[color:var(--text-secondary)]">Voz do Narrador</label>
                <select
                  value={selectedBook.voice_name || 'pt-BR-FranciscaNeural'}
                  onChange={handleVoiceChange}
                  className="alfredo-input w-full cursor-pointer py-2 text-[13px]"
                >
                  {voices.map(v => (
                    <option key={v.id} value={v.id}>{v.name}</option>
                  ))}
                </select>
              </div>

              <div className="mt-2 grid grid-cols-3 gap-2 border-b border-[color:var(--border-color)] pb-6">
                <button onClick={() => handlePlay()} className="alfredo-pill flex-col justify-center border-brass-500/25 bg-brass-500/10 py-3 text-brass-300 hover:bg-brass-500/20">
                  <Play className="h-4 w-4" />
                  <span className="mt-1 text-[10px] font-bold uppercase tracking-wider">Tocar</span>
                </button>
                <button onClick={() => handlePause()} className="alfredo-pill flex-col justify-center py-3 hover:bg-[color:var(--surface-hover)]">
                  <Pause className="h-4 w-4" />
                  <span className="mt-1 text-[10px] font-bold uppercase tracking-wider">Pausar</span>
                </button>
                <button onClick={() => handleResume()} className="alfredo-pill flex-col justify-center border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10">
                  <PlayCircle className="h-4 w-4" />
                  <span className="mt-1 text-[10px] font-bold uppercase tracking-wider">Retomar</span>
                </button>
              </div>
            </div>
              
              <div className="h-px w-full bg-white/5" />

              <button
                onClick={() => handleDelete(selectedBook.id)}
                disabled={isDeleting === selectedBook.id}
                className="alfredo-pill border-rose-500/20 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 justify-center"
              >
                {isDeleting === selectedBook.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                Excluir Livro
              </button>
            </div>

            {/* Chapters List */}
            <div className="flex-1 min-w-0">
              <h3 className="alfredo-section-label mb-4 flex items-center gap-2">
                <BookMarked className="h-4 w-4 text-brass-400" /> 
                Capítulos ({selectedBook.chapters.length})
              </h3>
              
              {selectedBook.chapters.length === 0 ? (
                <div className="rounded-xl border border-white/5 bg-white/[0.02] p-8 text-center text-[13px] text-[color:var(--text-secondary)]">
                  Nenhum capítulo processado ainda.
                </div>
              ) : (
                <div className="flex max-h-[60vh] flex-col gap-2 overflow-y-auto pr-2">
                  {selectedBook.chapters.map((chapter) => (
                    <div
                      key={chapter.id}
                      className="group flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] p-3 hover:bg-white/[0.04]"
                    >
                      <div className="flex items-center gap-3 overflow-hidden">
                        <span className="shrink-0 font-mono text-[11px] text-[color:var(--text-tertiary)]">
                          {(chapter.index + 1).toString().padStart(2, '0')}
                        </span>
                        <span className="truncate text-[13px] font-medium text-[color:var(--text-primary)]">
                          {chapter.title || `Capítulo ${chapter.index + 1}`}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-4 shrink-0 ml-4">
                        <div className="flex items-center gap-2">
                          <div 
                            title={chapter.has_annotation ? "Com anotações" : "Sem anotações"}
                            className={cn(
                              "h-2 w-2 rounded-full",
                              chapter.has_annotation ? "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)]" : "bg-white/10"
                            )} 
                          />
                          <div 
                            title={chapter.has_audio ? "Áudio pronto" : "Aguardando processamento de áudio"}
                            className={cn(
                              "h-2 w-2 rounded-full",
                              chapter.has_audio ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" : "bg-white/10"
                            )} 
                          />
                        </div>
                        
                        <button
                          onClick={() => handlePlay(chapter.index)}
                          className="rounded-full bg-brass-500/10 p-1.5 text-brass-300 opacity-0 transition-opacity hover:bg-brass-500/20 group-hover:opacity-100"
                          title="Tocar este capítulo"
                        >
                          <Play className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
