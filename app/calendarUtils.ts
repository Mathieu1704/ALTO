import * as Calendar from 'expo-calendar';

function getDateRangeFromPeriod(period: string): { start: Date; end: Date } {
  const now = new Date();
  const start = new Date(now);
  const end = new Date(now);

  switch (period.toLowerCase()) {
    case 'aujourd\'hui':
      start.setHours(0, 0, 0, 0);
      end.setHours(23, 59, 59, 999);
      break;

    case 'demain':
      start.setDate(start.getDate() + 1);
      start.setHours(0, 0, 0, 0);
      end.setDate(start.getDate());
      end.setHours(23, 59, 59, 999);
      break;

    case 'cette semaine':
      const day = now.getDay(); // 0 (dim) à 6 (sam)
      const diffToMonday = day === 0 ? -6 : 1 - day;
      start.setDate(start.getDate() + diffToMonday);
      start.setHours(0, 0, 0, 0);
      end.setDate(start.getDate() + 6);
      end.setHours(23, 59, 59, 999);
      break;

    case 'ce week-end':
      const saturday = new Date(now);
      saturday.setDate(now.getDate() + ((6 - now.getDay()) % 7));
      saturday.setHours(0, 0, 0, 0);
      const sunday = new Date(saturday);
      sunday.setDate(saturday.getDate() + 1);
      sunday.setHours(23, 59, 59, 999);
      return { start: saturday, end: sunday };

    case 'semaine prochaine':
      const nextMonday = new Date(now);
      const offset = (8 - now.getDay()) % 7;
      nextMonday.setDate(now.getDate() + offset);
      nextMonday.setHours(0, 0, 0, 0);
      const nextSunday = new Date(nextMonday);
      nextSunday.setDate(nextMonday.getDate() + 6);
      nextSunday.setHours(23, 59, 59, 999);
      return { start: nextMonday, end: nextSunday };

    default:
      start.setHours(0, 0, 0, 0);
      end.setHours(23, 59, 59, 999);
      break;
  }

  return { start, end };
}

export async function getEventsForPeriod(period: string): Promise<string> {
  const { status } = await Calendar.requestCalendarPermissionsAsync();
  if (status !== 'granted') {
    return "Permission refusée pour accéder au calendrier.";
  }

  const calendars = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
  const calendarIds = calendars.map(c => c.id);

  const { start, end } = getDateRangeFromPeriod(period);

  const events = await Calendar.getEventsAsync(calendarIds, start, end);

  if (events.length === 0) {
    return `Tu n'as aucun événement prévu pour ${period}.`;
  }

  let result = `Voici tes événements pour ${period} :\n`;
  for (const e of events) {
    const startDate = new Date(e.startDate);
    const endDate = new Date(e.endDate);

    const startTime = startDate.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    const endTime = endDate.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

    result += `• Tu as "${e.title ?? "un événement"}" prévu de ${startTime} à ${endTime} heures.\n`;
  }

  return result.trim();
}
