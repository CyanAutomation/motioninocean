/** Select the mascot image and accessible label shown for a viewer tab. */
export function getMioMascotForTab(tabName, assets) {
    const mascotByTab = {
        main: { src: assets.happy, alt: "Mio mascot for Stream view" },
        config: { src: assets.curious, alt: "Mio mascot for Configuration view" },
        setup: { src: assets.avatar, alt: "Mio mascot for Set-Up view" },
        settings: { src: assets.sleeping, alt: "Mio mascot for Runtime Settings view" },
    };
    return mascotByTab[tabName] || mascotByTab.main;
}
/** Apply the selected mascot image and accessible label when the hero image exists. */
export function updateMioMascotForTab(tabName, imageElement, assets) {
    if (!imageElement)
        return;
    const mascot = getMioMascotForTab(tabName, assets);
    imageElement.src = mascot.src;
    imageElement.alt = mascot.alt;
}
