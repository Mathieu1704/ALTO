// calendarUtils.ts
import * as Calendar from 'expo-calendar';

/*--------------------------------------------------------------*/
/* 1. Convertit période OU date explicite → plage de dates       */
/*--------------------------------------------------------------*/
function getDateRangeFromPeriod(period: string): { start: Date; end: Date } {
  const now   = new Date();
  const start = new Date(now);
  const end   = new Date(now);

  const lc = period.toLowerCase().trim();
  const setFull = (d: Date, h: number, m = 0, s = 0, ms = 0) =>
    d.setHours(h, m, s, ms);

  /* ---------- A. yyyy-mm-dd (2025-05-20) --------------------- */
  const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(lc);
  if (iso) {
    const [_, y, m, d] = iso;
    const s = new Date(Number(y), Number(m) - 1, Number(d), 0, 0, 0, 0);
    const e = new Date(s); e.setHours(23, 59, 59, 999);
    return { start: s, end: e };
  }

  /* ---------- B. dd/mm/yyyy ou dd-mm-yyyy -------------------- */
  const frNum = /^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/.exec(lc);
  if (frNum) {
    const [_, d, m, y] = frNum;
    const s = new Date(Number(y), Number(m) - 1, Number(d), 0, 0, 0, 0);
    const e = new Date(s); e.setHours(23, 59, 59, 999);
    return { start: s, end: e };
  }

  /* ---------- C. "20 mai 2025" ou "20 mai" ------------------- */
  const months = [
    'janvier','février','mars','avril','mai','juin',
    'juillet','août','septembre','octobre','novembre','décembre'
  ];

  const frFull = /^(\d{1,2})\s+([a-zéûîôàè]+)\s+(\d{4})$/.exec(lc);
  if (frFull) {
    const [_, d, monthName, y] = frFull;
    const mIndex = months.indexOf(monthName);
    if (mIndex !== -1) {
      const s = new Date(Number(y), mIndex, Number(d), 0, 0, 0, 0);
      const e = new Date(s); e.setHours(23, 59, 59, 999);
      return { start: s, end: e };
    }
  }

  const frNoYear = /^(\d{1,2})\s+([a-zéûîôàè]+)$/.exec(lc);
  if (frNoYear) {
    const [_, d, monthName] = frNoYear;
    const mIndex = months.indexOf(monthName);
    if (mIndex !== -1) {
      const s = new Date(now.getFullYear(), mIndex, Number(d), 0, 0, 0, 0);
      const e = new Date(s); e.setHours(23, 59, 59, 999);
      // si la date est déjà passée cette année, on décale à l’an prochain
      if (e < now) { s.setFullYear(s.getFullYear() + 1); e.setFullYear(e.getFullYear() + 1); }
      return { start: s, end: e };
    }
  }

  /* ---------- D. Périodes relatives -------------------------- */
  switch (lc) {
    case "aujourd'hui":
    case 'today':
      setFull(start, 0);
      setFull(end, 23, 59, 59, 999);
      break;

    case 'demain':
    case 'tomorrow':
      start.setDate(start.getDate() + 1);
      end.setDate(start.getDate());
      setFull(start, 0);
      setFull(end, 23, 59, 59, 999);
      break;

    case 'cette semaine':
    case 'this week': {
      // Lundi-dimanche
      const diffMon = (now.getDay() + 6) % 7; // 0=lundi
      start.setDate(start.getDate() - diffMon);
      end.setDate(start.getDate() + 6);
      setFull(start, 0);
      setFull(end, 23, 59, 59, 999);
      break;
    }

    case 'ce week-end':
    case 'week-end': {
      const toSat = (6 - now.getDay() + 7) % 7; // samedi
      start.setDate(now.getDate() + toSat);
      end.setDate(start.getDate() + 1);
      setFull(start, 0);
      setFull(end, 23, 59, 59, 999);
      break;
    }

    case 'semaine prochaine':
    case 'next week': {
      const toNextMon = (8 - now.getDay()) % 7 || 7;
      start.setDate(now.getDate() + toNextMon);
      end.setDate(start.getDate() + 6);
      setFull(start, 0);
      setFull(end, 23, 59, 59, 999);
      break;
    }

    default:
      // Par défaut → aujourd’hui
      setFull(start, 0);
      setFull(end, 23, 59, 59, 999);
  }

  return { start, end };
}

/*--------------------------------------------------------------*/
/* 2. Récupère et formate les événements                         */
/*--------------------------------------------------------------*/
export async function getEventsForPeriod(period: string): Promise<string> {
  const { status } = await Calendar.requestCalendarPermissionsAsync();
  if (status !== 'granted') {
    return "Je n'ai pas la permission d'accéder à ton agenda.";
  }

  const calendars   = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
  const calendarIds = calendars.map(c => c.id);

  const { start, end } = getDateRangeFromPeriod(period);

  const events = await Calendar.getEventsAsync(calendarIds, start, end);

  if (!events.length) {
    return `Aucun événement prévu ${
      period === "aujourd'hui" ? 'aujourd’hui' : `pour ${period}`
    }.`;
  }

  const fmt = new Intl.DateTimeFormat('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  });

  const lines = events.map(ev => {
    const deb = fmt.format(new Date(ev.startDate));
    const fin = fmt.format(new Date(ev.endDate));
    return `• “${ev.title || 'Événement'}” de ${deb} à ${fin}`;
  });

  return `Voici tes événements ${period} :\n${lines.join('\n')}`;
}
