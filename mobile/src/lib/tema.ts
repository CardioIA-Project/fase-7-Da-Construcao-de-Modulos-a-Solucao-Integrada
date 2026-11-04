export const cores = {
  fundo: "#F2F5F6",
  superficie: "#FFFFFF",
  borda: "#DCE6E6",
  texto: "#12262B",
  suave: "#5B6E70",
  marca: "#0F6E7A",
  marcaEscura: "#0B3D3D",
  baixo: "#2C8A55",
  baixoFundo: "#E1F4EA",
  moderado: "#C98A00",
  moderadoFundo: "#FFF1CC",
  alto: "#C62F3B",
  altoFundo: "#FBE9E6",
};

export function corDoRisco(nivel: string | null | undefined) {
  if (nivel === "ALTO") return { cor: cores.alto, fundo: cores.altoFundo };
  if (nivel === "MODERADO") return { cor: cores.moderado, fundo: cores.moderadoFundo };
  if (nivel === "BAIXO") return { cor: cores.baixo, fundo: cores.baixoFundo };
  return { cor: cores.suave, fundo: cores.borda };
}
