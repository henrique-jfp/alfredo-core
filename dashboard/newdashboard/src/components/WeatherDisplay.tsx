// WeatherDisplay.tsx → re-exporta do WeatherTab para manter compatibilidade
// com OverviewTab e quaisquer outros componentes que importem daqui.
// Os SVGs com animação, gradientes e useId() estão todos em WeatherTab.tsx.
export { WeatherDisplay, WeatherIconByCode } from './tabs/WeatherTab';
export type { WeatherIconSize } from './tabs/WeatherTab';
