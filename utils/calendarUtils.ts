// calendarUtils.ts
import { parse } from 'date-fns';
import { fr } from 'date-fns/locale';
import * as Calendar from 'expo-calendar';
import * as IntentLauncher from 'expo-intent-launcher'; // MODIF: import pour lancer l’UI native Android
import { Linking, Platform } from 'react-native'; // MODIF: import pour deep-link iOS

/*--------------------------------------------------------------*/
/* 1. Convertit période OU date précise → plage de dates         */
/*--------------------------------------------------------------*/
function getDateRangeFromPeriod(period: string): { start: Date; end: Date } {
  const now   = new Date();
  const start = new Date(now);
  const end   = new Date(now);

  const lc = period.toLowerCase().trim();
  const setFull = (d: Date, h: number, m = 0, s = 0, ms = 0) =>
    d.setHours(h, m, s, ms);

  /* ---------- A. Date précise yyyy-mm-dd -------------------- */
  const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(lc);
  if (iso) {
    const [_, y, m, d] = iso;
    const s = new Date(Number(y), Number(m) - 1, Number(d), 0, 0, 0, 0);
    const e = new Date(s); e.setHours(23, 59, 59, 999);
    return { start: s, end: e };
  }

  /* ---------- B. Date précise dd/mm/yyyy ou dd-mm-yyyy ------- */
  const frNum = /^(\d{2})[\/\-](\d{2})[\/\-](\d{4})$/.exec(lc);
  if (frNum) {
    const [_, d, m, y] = frNum;
    const s = new Date(Number(y), Number(m) - 1, Number(d), 0, 0, 0, 0);
    const e = new Date(s); e.setHours(23, 59, 59, 999);
    return { start: s, end: e };
  }

  /* ---------- C. “20 mai 2025” ou “20 mai” ------------------- */
  try {
    const parsed = parse(lc, 'd MMM yyyy', new Date(), { locale: fr });
    if (!isNaN(parsed.getTime())) {
      const s = new Date(parsed.setHours(0, 0, 0, 0));
      const e = new Date(parsed.setHours(23, 59, 59, 999));
      return { start: s, end: e };
    }
  } catch { /* ignore parse errors */ }

  try {
    const parsedNoYear = parse(lc, 'd MMM', new Date(), { locale: fr });
    if (!isNaN(parsedNoYear.getTime())) {
      const year = parsedNoYear.getFullYear() === 1900
        ? now.getFullYear()
        : parsedNoYear.getFullYear();
      parsedNoYear.setFullYear(year);
      if (parsedNoYear < now) parsedNoYear.setFullYear(year + 1); // date déjà passée
      const s = new Date(parsedNoYear.setHours(0, 0, 0, 0));
      const e = new Date(parsedNoYear.setHours(23, 59, 59, 999));
      return { start: s, end: e };
    }
  } catch { /* ignore parse errors */ }

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
      const diffMon = (now.getDay() + 6) % 7; // 0 = lundi
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

/*--------------------------------------------------------------*/
/* MODIF: Ajout de la logique pour ouvrir l’UI native du calendrier */
/*--------------------------------------------------------------*/

/**
 * Lance l'UI de création d'événement dans le calendrier natif.
 */
export function launchNativeCalendarEvent(
  title: string,
  start: Date,
  end: Date
): void {
  if (Platform.OS === 'android') {
    IntentLauncher.startActivityAsync(
      'android.intent.action.INSERT',            // MODIF: remplacer IntentLauncher.ACTION_INSERT
      {
        data: 'content://com.android.calendar/events',
        extra: {                                // MODIF: c'est `extra` (singulier), pas `extras`
          title,
          beginTime: start.getTime(),
          endTime:   end.getTime(),
          allDay:    false,
        },
      }
    );
  } else if (Platform.OS === 'ios') {
    const ts = Math.floor(start.getTime() / 1000);
    Linking.openURL(`calshow:${ts}`);
  } else {
    console.warn('Calendrier natif non pris en charge sur cette plateforme');
  }
}

/**
 * À appeler depuis le front quand GPT déclenche la function_call "open_native_calendar".
 */
export function scheduleAppointmentViaNativeUI(
  summary: string,
  isoStart:   string,
  durationMinutes: number = 60
): void {
  const start = new Date(isoStart);
  const end   = new Date(start.getTime() + durationMinutes * 60000);
  launchNativeCalendarEvent(summary, start, end);
}