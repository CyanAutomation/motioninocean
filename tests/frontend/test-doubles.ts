type DeepPartial<T> = T extends (...args: infer Args) => infer Result
  ? (...args: Args) => DeepPartial<Result>
  : T extends readonly (infer Item)[]
    ? readonly DeepPartial<Item>[]
    : T extends object
      ? { [Key in keyof T]?: DeepPartial<T[Key]> }
      : T;

/** Cast a deliberately partial fixture after checking the fields it supplies. */
export function asTestDouble<T>(fixture: DeepPartial<T>): T {
  return fixture as unknown as T;
}
