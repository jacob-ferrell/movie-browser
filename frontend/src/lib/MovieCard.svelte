<script>
  import { fetchProviders } from './api.js'
  import { getState, setFlag } from './itemStates.svelte.js'

  let { item, onFindTorrents } = $props()

  let expanded = $state(false)
  let providers = $state(null)
  let loadingProviders = $state(false)
  let flagging = $state(null) // which flag is being saved

  let state = $derived(getState(item.id, item.media_type))

  const year = (date) => date ? date.slice(0, 4) : '—'

  const ratingColor = (r) => {
    if (r >= 7.5) return 'text-emerald-400'
    if (r >= 6.0) return 'text-amber-400'
    return 'text-red-400'
  }

  async function toggleExpand() {
    expanded = !expanded
    if (expanded && !providers) {
      loadingProviders = true
      try {
        providers = await fetchProviders(item.media_type, item.id)
      } catch {
        providers = { stream: [], rent: [], buy: [], link: null }
      } finally {
        loadingProviders = false
      }
    }
  }

  async function toggle(flag) {
    flagging = flag
    try {
      await setFlag(item.id, item.media_type, item.title, item.poster_url, flag, !state[flag])
    } finally {
      flagging = null
    }
  }
</script>

<div class="group relative flex flex-col bg-gray-900 rounded-xl overflow-hidden w-full border border-gray-800 hover:border-gray-600 transition-all duration-200 hover:scale-[1.02] hover:shadow-xl hover:shadow-black/50">

  <!-- Poster (clickable to expand) -->
  <div
    class="relative aspect-[2/3] w-full bg-gray-800 overflow-hidden cursor-pointer"
    role="button"
    tabindex="0"
    aria-expanded={expanded}
    onclick={toggleExpand}
    onkeydown={(e) => e.key === 'Enter' && toggleExpand()}
  >
    {#if item.poster_url}
      <img
        src={item.poster_url}
        alt={item.title}
        loading="lazy"
        class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
      />
    {:else}
      <div class="w-full h-full flex items-center justify-center text-gray-600">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
        </svg>
      </div>
    {/if}

    <!-- Media type badge -->
    <span class="absolute top-2 left-2 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full {item.media_type === 'tv' ? 'bg-purple-600/90 text-purple-100' : 'bg-blue-600/90 text-blue-100'}">
      {item.media_type === 'tv' ? 'TV' : 'Film'}
    </span>

    <!-- Rating badge -->
    {#if item.vote_average > 0}
      <span class="absolute top-2 right-2 text-xs font-bold px-2 py-0.5 rounded-full bg-gray-950/80 {ratingColor(item.vote_average)}">
        ★ {item.vote_average}
      </span>
    {/if}

    <!-- State badges (bottom of poster) -->
    {#if state.watched || state.downloaded}
      <div class="absolute bottom-2 left-2 flex gap-1">
        {#if state.watched}
          <span class="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-600/90 text-white">✓ Watched</span>
        {/if}
        {#if state.downloaded}
          <span class="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-teal-700/90 text-white">↓ Downloaded</span>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Card body -->
  <div class="p-3 flex flex-col gap-1 flex-1">
    <h3 class="text-sm font-semibold text-gray-100 leading-tight line-clamp-2">{item.title}</h3>
    <p class="text-xs text-gray-500">{year(item.release_date)}</p>

    <!-- Action buttons row -->
    <div class="mt-1.5 flex gap-1">
      <button
        title={state.watched ? 'Mark as unwatched' : 'Mark as watched'}
        onclick={() => toggle('watched')}
        disabled={flagging === 'watched'}
        class="flex-1 flex items-center justify-center gap-1 py-2.5 rounded-lg text-xs font-medium transition disabled:opacity-50
          {state.watched ? 'bg-emerald-700/60 text-emerald-300 hover:bg-emerald-700' : 'bg-gray-800 text-gray-500 hover:bg-gray-700 hover:text-gray-200'}"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
        {state.watched ? 'Watched' : 'Watch'}
      </button>
      <button
        title={state.not_interested ? 'Remove not interested' : 'Not interested'}
        onclick={() => toggle('not_interested')}
        disabled={flagging === 'not_interested'}
        class="flex-1 flex items-center justify-center gap-1 py-2.5 rounded-lg text-xs font-medium transition disabled:opacity-50
          {state.not_interested ? 'bg-red-900/50 text-red-400 hover:bg-red-900' : 'bg-gray-800 text-gray-500 hover:bg-gray-700 hover:text-gray-200'}"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
        </svg>
        {state.not_interested ? 'Undo' : 'Skip'}
      </button>
    </div>

    {#if onFindTorrents}
      <button
        class="mt-1 w-full flex items-center justify-center gap-1.5 py-2.5 rounded-lg bg-gray-800 hover:bg-teal-700 text-gray-400 hover:text-white text-xs font-medium transition"
        onclick={(e) => { e.stopPropagation(); onFindTorrents(item.title, item.media_type, item.id, item.poster_url) }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Find Torrents
      </button>
    {/if}
  </div>

  <!-- Expanded section -->
  {#if expanded}
    <div class="px-3 pb-3 border-t border-gray-800 pt-3 flex flex-col gap-3">
      {#if item.overview}
        <p class="text-xs text-gray-400 leading-relaxed line-clamp-4">{item.overview}</p>
      {/if}

      {#if loadingProviders}
        <div class="flex gap-1">
          {#each [1,2,3] as _}
            <div class="w-8 h-8 rounded-md bg-gray-700 animate-pulse"></div>
          {/each}
        </div>
      {:else if providers}
        {#if providers.stream.length > 0}
          <div>
            <p class="text-[10px] uppercase tracking-wider text-teal-500 font-semibold mb-1.5">Stream</p>
            <div class="flex flex-wrap gap-1.5">
              {#each providers.stream as p}
                <img src={p.logo_url} alt={p.name} title={p.name} class="w-8 h-8 rounded-md object-cover" loading="lazy" />
              {/each}
            </div>
          </div>
        {/if}
        {#if providers.rent.length > 0}
          <div>
            <p class="text-[10px] uppercase tracking-wider text-amber-500 font-semibold mb-1.5">Rent</p>
            <div class="flex flex-wrap gap-1.5">
              {#each providers.rent as p}
                <img src={p.logo_url} alt={p.name} title={p.name} class="w-8 h-8 rounded-md object-cover" loading="lazy" />
              {/each}
            </div>
          </div>
        {/if}
        {#if providers.buy.length > 0}
          <div>
            <p class="text-[10px] uppercase tracking-wider text-blue-400 font-semibold mb-1.5">Buy</p>
            <div class="flex flex-wrap gap-1.5">
              {#each providers.buy as p}
                <img src={p.logo_url} alt={p.name} title={p.name} class="w-8 h-8 rounded-md object-cover" loading="lazy" />
              {/each}
            </div>
          </div>
        {/if}
        {#if providers.stream.length === 0 && providers.rent.length === 0 && providers.buy.length === 0}
          <p class="text-xs text-gray-600">No streaming info available in your region.</p>
        {/if}
        {#if providers.link}
          <a
            href={providers.link}
            target="_blank"
            rel="noopener noreferrer"
            class="text-[10px] text-teal-500 hover:text-teal-400 underline mt-1"
            onclick={(e) => e.stopPropagation()}
          >
            View on JustWatch →
          </a>
        {/if}
      {/if}
    </div>
  {/if}
</div>
