import { useEffect, useState } from 'react';
import { Check, ClipboardCopy, Download, ExternalLink, Hand, Loader2, Share2 } from 'lucide-react';
import { fetchFullVideo, type Reel } from './api';
import { useAct } from './hooks';
import { useToast } from './toast';
import { INPUT } from './ui';

const canShareFiles = (f: File) => typeof navigator.canShare === 'function' && navigator.canShare({ files: [f] });

/**
 * Posting by hand while the Instagram API isn't connected: get the full-quality video onto the phone,
 * copy the caption, post in the Instagram app, then mark it posted so the schedule stays right.
 * Two taps for the video on purpose: iOS only opens the share sheet straight after a tap,
 * not after a download that took a few seconds.
 */
export function ManualPost({ reel, compact }: { reel: Reel; compact?: boolean }) {
  const toast = useToast();
  const act = useAct('Marked as posted');
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [link, setLink] = useState('');
  useEffect(() => { setFile(null); setProgress(null); setCopied(false); setLink(''); }, [reel.id]);

  const prepare = async () => {
    setProgress(0);
    try {
      setFile(await fetchFullVideo(reel.id, setProgress));
    } catch (e) {
      toast.show((e as Error).message, { tone: 'error' });
    } finally {
      setProgress(null);
    }
  };

  const save = async () => {
    if (!file) return;
    if (canShareFiles(file)) {
      try {
        await navigator.share({ files: [file] });
      } catch (e) {
        if ((e as Error).name !== 'AbortError') toast.show('Could not open sharing. Try again.', { tone: 'error' });
      }
      return;
    }
    const url = URL.createObjectURL(file);
    const a = Object.assign(document.createElement('a'), { href: url, download: file.name });
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(reel.caption);
      setCopied(true);
      toast.show('Caption copied');
    } catch {
      toast.show('Copy failed: press and hold the caption text to copy it.', { tone: 'error' });
    }
  };

  const btn = 'flex h-10 w-full cursor-pointer items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold disabled:cursor-default disabled:opacity-50';
  const step = 'flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-bold text-white';

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-accent/40 bg-accent-light/60 p-3">
      <p className="flex items-center gap-2 text-sm font-semibold text-accent">
        <Hand className="h-4 w-4" aria-hidden="true" /> Post manually
        {!compact && <span className="font-normal text-ink-mute">· until Instagram is connected</span>}
      </p>

      <div className="flex items-start gap-2.5">
        <span className={step}>1</span>
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          {!file ? (
            <button type="button" onClick={prepare} disabled={progress !== null} className={`${btn} bg-accent text-white hover:bg-accent-dark`}>
              {progress !== null ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Download className="h-4 w-4" aria-hidden="true" />}
              {progress !== null ? `Getting video… ${Math.round(progress * 100)}%` : 'Get the full-quality video'}
            </button>
          ) : (
            <button type="button" onClick={save} className={`${btn} bg-accent text-white hover:bg-accent-dark`}>
              <Share2 className="h-4 w-4" aria-hidden="true" /> Save video ({(file.size / 1e6).toFixed(1)} MB)
            </button>
          )}
          <p className="text-xs text-ink-mute">{file ? 'On iPhone choose “Save Video” (or share straight to Instagram).' : 'About 5 MB, 1080×1920.'}</p>
        </div>
      </div>

      <div className="flex items-start gap-2.5">
        <span className={step}>2</span>
        <button type="button" onClick={copy} className={`${btn} border border-paper-line bg-paper text-ink hover:bg-paper-alt`}>
          {copied ? <Check className="h-4 w-4 text-ok" aria-hidden="true" /> : <ClipboardCopy className="h-4 w-4" aria-hidden="true" />}
          {copied ? 'Caption copied' : 'Copy caption'}
        </button>
      </div>

      <div className="flex items-start gap-2.5">
        <span className={step}>3</span>
        <a href="https://www.instagram.com/" target="_blank" rel="noreferrer" className={`${btn} border border-paper-line bg-paper text-ink hover:bg-paper-alt`}>
          <ExternalLink className="h-4 w-4" aria-hidden="true" /> Open Instagram and post the Reel
        </a>
      </div>

      <form className="flex items-start gap-2.5" onSubmit={(e) => { e.preventDefault(); act.mutate({ type: 'mark_posted', id: reel.id, permalink: link.trim() || undefined }); }}>
        <span className={step}>4</span>
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <input value={link} onChange={(e) => setLink(e.target.value)} inputMode="url" placeholder="Reel link (optional): Share → Copy link"
            className={INPUT} aria-label="Instagram link of the posted reel" />
          <button type="submit" disabled={act.isPending} className={`${btn} border border-accent text-accent hover:bg-accent/10`}>
            <Check className="h-4 w-4" aria-hidden="true" /> I posted it
          </button>
        </div>
      </form>
    </div>
  );
}
