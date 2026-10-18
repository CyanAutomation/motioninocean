export interface MioMascotAssets {
  avatar: string;
  curious: string;
  floating: string;
  happy: string;
  sleeping: string;
  winking: string;
}

export interface MioMascotSelection {
  src: string;
  alt: string;
}

export interface MioMascotImage {
  src: string;
  alt: string;
}

/** Select the mascot image and accessible label shown for a viewer tab. */
export function getMioMascotForTab(
  tabName: string,
  assets: MioMascotAssets,
): MioMascotSelection {
  const mascotByTab: Record<string, MioMascotSelection> = {
    main: { src: assets.happy, alt: "Mio mascot for Stream view" },
    config: { src: assets.curious, alt: "Mio mascot for Configuration view" },
    setup: { src: assets.avatar, alt: "Mio mascot for Set-Up view" },
    settings: { src: assets.sleeping, alt: "Mio mascot for Runtime Settings view" },
  };

  return mascotByTab[tabName] || mascotByTab.main!;
}

/** Apply the selected mascot image and accessible label when the hero image exists. */
export function updateMioMascotForTab(
  tabName: string,
  imageElement: MioMascotImage | null,
  assets: MioMascotAssets,
): void {
  if (!imageElement) return;

  const mascot = getMioMascotForTab(tabName, assets);
  imageElement.src = mascot.src;
  imageElement.alt = mascot.alt;
}
