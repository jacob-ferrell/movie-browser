import { fetchItemStates, markItem } from './api.js'

// Reactive map: "tmdbId:mediaType" → { watched, not_interested, downloaded }
let states = $state({})

export function getState(tmdbId, mediaType) {
  return states[`${tmdbId}:${mediaType}`] ?? { watched: false, not_interested: false, downloaded: false }
}

export async function loadStates(items) {
  const data = await fetchItemStates(items)
  Object.assign(states, data)
}

export async function setFlag(tmdbId, mediaType, title, posterUrl, flag, value = true) {
  const row = await markItem(tmdbId, mediaType, title, posterUrl, flag, value)
  states[`${tmdbId}:${mediaType}`] = {
    watched: row.watched,
    not_interested: row.not_interested,
    downloaded: row.downloaded,
  }
  return row
}
