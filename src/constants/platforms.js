export const platforms = {
    global: [
        { id: "spotify",      name: "Spotify",       color: "#1DB954", initial: "S" },
        { id: "appleMusic",   name: "Apple\nMusic",  color: "#FA243C", initial: "A" },
        { id: "youtube",      name: "YouTube",       color: "#FF0000", initial: "Y" },
        { id: "youtubeMusic", name: "YT Music",      color: "#FF0000", initial: "Y" },
        { id: "amazon",       name: "Amazon",        color: "#00A8E1", initial: "a" },
    ],
    korea: [
        { id: "melon",        name: "Melon",         color: "#00CD3C", initial: "M" },
        { id: "bugs",         name: "Bugs",          color: "#FF3C28", initial: "B" },
        { id: "flo",          name: "FLO",           color: "#4115EE", initial: "F" },
    ]
}

export const deepLinks = {
    spotify: {
        intent: (id) => `intent://open.spotify.com/track/${id}#Intent;scheme=https;package=com.spotify.music;end`,
        web:    (id) => `https://open.spotify.com/track/${id}`,
    },
    appleMusic: {
        intent: (id) => `intent://music.apple.com/song/${id}#Intent;scheme=https;package=com.apple.android.music;end`,
        web:    (id) => `https://music.apple.com/kr/song/${id}`,
    },
    youtube: {
        intent: (id) => `intent://www.youtube.com/watch?v=${id}#Intent;scheme=https;package=com.google.android.youtube;end`,
        web:    (id) => `https://www.youtube.com/watch?v=${id}`,
    },
    youtubeMusic: {
        intent: (id) => `intent://music.youtube.com/watch?v=${id}#Intent;scheme=https;package=com.google.android.apps.youtube.music;end`,
        web:    (id) => `https://music.youtube.com/watch?v=${id}`,
    },
    melon: {
        intent: (id) => `intent://song/detail.htm?songId=${id}#Intent;scheme=melonapp;package=com.iloen.melon;end`,
        web:    (id) => `https://www.melon.com/song/detail.htm?songId=${id}`,
    },
    bugs: {
        intent: (id) => `intent://music.bugs.co.kr/track/${id}#Intent;scheme=https;package=com.neowiz.android.bugs;end`,
        web:    (id) => `https://music.bugs.co.kr/track/${id}`,
    },
    flo: {
        intent: (id) => `intent://www.music-flo.com/detail/track/${id}#Intent;scheme=https;package=skplanet.musicmate;end`,
        web:    (id) => `https://www.music-flo.com/detail/track/${id}/trackList.html`,
    },
    amazon: {
        intent: (id) => `intent://music.amazon.com/tracks/${id}#Intent;scheme=https;package=com.amazon.mp3;end`,
        web:    (id) => `https://music.amazon.com/tracks/${id}`,
    },
}