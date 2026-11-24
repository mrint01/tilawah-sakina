import { Bot, CalendarHeart, Sparkles } from 'lucide-react';
import { MAKE_TIME, REVIEW_TIME, SLOTS } from './api';
import { KindBadge } from './hooks';

/** The whole day in one list (Tunisia time): making, Claude's check, the 5 posts, and Friday's extra. */
export function DailyPlan({ bufferDays }: { bufferDays: number }) {
  const row = 'flex items-center gap-3 py-1.5 text-sm';
  const time = 'num w-12 shrink-0 font-semibold';
  return (
    <ul className="divide-y divide-paper-line">
      <li className={row}>
        <span className={time}>{MAKE_TIME}</span>
        <Sparkles className="h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
        <span className="text-ink-soft">New reels are made on GitHub, so each type has {bufferDays} days ready</span>
      </li>
      <li className={row}>
        <span className={time}>{REVIEW_TIME}</span>
        <Bot className="h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
        <span className="text-ink-soft">Claude watches each new reel and approves or rejects it</span>
      </li>
      {SLOTS.map((s) => (
        <li key={s.time} className={row}>
          <span className={time}>{s.time}</span>
          <KindBadge kind={s.kind} />
          <span className="text-ink-soft">
            {s.kind === 'ayah' && 'A surah passage on a nature video'}
            {s.kind === 'dua' && 'Morning adhkar, after-salah dua, a dua for a need, or salawat on Friday'}
            {s.kind === 'asma' && 'The next of the 99 Names, with an ayah'}
            {s.kind === 'tasbih' && '33 counts with the Kaaba'}
            {s.kind === 'quiz' && '“Guess the surah”, 5 questions'}
          </span>
        </li>
      ))}
      <li className={row}>
        <span className={time}>Fri</span>
        <CalendarHeart className="h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
        <span className="text-ink-soft">Also Surah Al-Kahf at 14:00 (part 1) and 14:10 (part 2)</span>
      </li>
    </ul>
  );
}
