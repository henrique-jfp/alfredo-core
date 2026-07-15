import { useState, useEffect } from 'react';
import { ForecastData } from '../types';

const WMO_MAP: Record<number, string> = {
  0: 'Céu limpo',
  1: 'Pred. limpo', 2: 'Parc. nublado', 3: 'Nublado',
  45: 'Nevoeiro', 48: 'Nevoeiro denso',
  51: 'Chuvisco leve', 53: 'Chuvisco', 55: 'Chuvisco denso',
  56: 'Chuvisco gelado', 57: 'Chuvisco g. denso',
  61: 'Chuva leve', 63: 'Chuva mod.', 65: 'Chuva forte',
  66: 'Chuva cong. leve', 67: 'Chuva cong. forte',
  71: 'Neve leve', 73: 'Neve mod.', 75: 'Neve forte',
  77: 'Grãos de neve',
  80: 'Pancada leve', 81: 'Pancada mod.', 82: 'Pancada forte',
  85: 'Nevasca leve', 86: 'Nevasca forte',
  95: 'Tempestade', 96: 'Tempestade (granizo)', 99: 'Tempestade severa'
};

export function getWmoDesc(code: number) {
  return WMO_MAP[code] || 'Desconhecido';
}

function parseIsoToUnix(isoString: string) {
  return Math.floor(new Date(isoString).getTime() / 1000);
}

const CACHE_KEY = 'alfredo_weather_cache';
const CACHE_TIME = 15 * 60 * 1000; // 15 mins

export function useWeather() {
  const [data, setData] = useState<ForecastData | null>(null);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;

    async function fetchData(lat: string, lon: string, city: string) {
      try {
        const forecastUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m,dew_point_2m,uv_index&hourly=temperature_2m,precipitation_probability,weather_code,dew_point_2m,uv_index,visibility&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,moonrise,moonset,moon_phase,uv_index_max,precipitation_probability_max,sunshine_duration,precipitation_sum&timezone=auto&forecast_days=7`;
        const aqiUrl = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&current=us_aqi,pm2_5,pm10,ozone`;

        const [resForecast, resAqi] = await Promise.all([
          fetch(forecastUrl),
          fetch(aqiUrl)
        ]);

        if (!resForecast.ok || !resAqi.ok) {
          throw new Error('Falha ao buscar dados da API');
        }

        const fc = await resForecast.json();
        const aqiData = await resAqi.json();

        // Mapear para ForecastData
        const now = Math.floor(Date.now() / 1000);
        
        const mappedData: ForecastData = {
          city,
          aqi: Math.round(aqiData.current?.us_aqi || 0),
          current: {
            temperature: Math.round(fc.current.temperature_2m).toString(),
            feels_like: Math.round(fc.current.apparent_temperature).toString(),
            humidity: fc.current.relative_humidity_2m.toString(),
            pressure: fc.current.pressure_msl.toString(),
            description: getWmoDesc(fc.current.weather_code),
            weather_code: fc.current.weather_code,
            icon: '', // não usado mais
            max_temp: Math.round(fc.daily.temperature_2m_max[0]).toString(),
            min_temp: Math.round(fc.daily.temperature_2m_min[0]).toString(),
            wind_speed: fc.current.wind_speed_10m.toString(),
            wind_deg: fc.current.wind_direction_10m,
            visibility: fc.hourly.visibility[0] || 10000,
            sunrise: parseIsoToUnix(fc.daily.sunrise[0]),
            sunset: parseIsoToUnix(fc.daily.sunset[0]),
            uvi: fc.current.uv_index,
            dew_point: fc.current.dew_point_2m,
            wind_gust: fc.current.wind_gusts_10m,
            rain: { "1h": fc.current.precipitation },
            is_day: fc.current.is_day
          },
          hourly: fc.hourly.time.map((t: string, i: number) => ({
            dt: parseIsoToUnix(t),
            time: new Date(t).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
            date: t.split('T')[0],
            temp: Math.round(fc.hourly.temperature_2m[i]),
            feels_like: Math.round(fc.hourly.temperature_2m[i]), // fallback
            humidity: 0,
            weather_code: fc.hourly.weather_code[i],
            description: getWmoDesc(fc.hourly.weather_code[i]),
            icon: '',
            wind_speed: 0,
            pop: fc.hourly.precipitation_probability[i] || 0
          })).filter((h: any) => h.dt >= now - 3600), // filta apenas as próximas horas
          daily: fc.daily.time.map((t: string, i: number) => ({
            date: t,
            max_temp: Math.round(fc.daily.temperature_2m_max[i]),
            min_temp: Math.round(fc.daily.temperature_2m_min[i]),
            weather_code: fc.daily.weather_code[i],
            description: getWmoDesc(fc.daily.weather_code[i]),
            pop: fc.daily.precipitation_probability_max[i] || 0,
            moon_phase: fc.daily.moon_phase[i],
            sunrise: parseIsoToUnix(fc.daily.sunrise[i]),
            sunset: parseIsoToUnix(fc.daily.sunset[i]),
            moonrise: fc.daily.moonrise[i] ? parseIsoToUnix(fc.daily.moonrise[i]) : undefined,
            moonset: fc.daily.moonset[i] ? parseIsoToUnix(fc.daily.moonset[i]) : undefined,
            sunshine_duration: fc.daily.sunshine_duration[i]
          }))
        };

        const cacheObj = {
          timestamp: Date.now(),
          data: mappedData
        };
        localStorage.setItem(CACHE_KEY, JSON.stringify(cacheObj));

        if (mounted) {
          setData(mappedData);
          setLoading(false);
        }
      } catch (err: any) {
        if (mounted) {
          setError(err.message);
          setLoading(false);
        }
      }
    }

    // Check cache first
    const cachedStr = localStorage.getItem(CACHE_KEY);
    if (cachedStr) {
      try {
        const cacheObj = JSON.parse(cachedStr);
        if (Date.now() - cacheObj.timestamp < CACHE_TIME) {
          setData(cacheObj.data);
          setLoading(false);
          return;
        }
      } catch(e) {}
    }

    // Use Geolocation or Fallback
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          fetchData(pos.coords.latitude.toString(), pos.coords.longitude.toString(), "Localização Atual");
        },
        (err) => {
          // Fallback Rio de Janeiro
          fetchData("-22.9068", "-43.1729", "Rio de Janeiro");
        },
        { timeout: 5000 }
      );
    } else {
      fetchData("-22.9068", "-43.1729", "Rio de Janeiro");
    }

    return () => {
      mounted = false;
    };
  }, []);

  return { data, error, loading };
}
