import { useMemo } from 'react'
import { encode } from 'uqr'

// 여백(quiet zone)은 4모듈이 표준이다. uqr 기본값은 1이라 부족하다.
// 여백이 모자라면 스캐너가 코드의 경계를 못 찾는다.
const BORDER = 4

// ECC 'M' — 49자 URL 기준 41x41(여백 포함). 'L'은 2모듈밖에 못 줄이고,
// 'H'는 49x49로 불어나는데 그만한 오류정정이 필요한 상황이 아니다
// (로고를 얹지 않으므로).
const ECC = 'M'

/**
 * URL 하나를 QR 코드 SVG 로 그린다.
 *
 * canvas 가 아니라 SVG 인 이유: 고해상도 폰에서 선명하고, 확대해도 안 깨지고,
 * 색을 CSS 가 아니라 명시적으로 지정할 수 있다.
 *
 * **색을 테마에 맡기지 않는 것이 중요하다.** 다크 모드에서 어두운 배경 위에
 * 어두운 QR 을 그리면 스캔이 안 된다. 그래서 배경은 항상 흰색, 모듈은 항상
 * 검은색으로 고정하고, 대신 카드 자체에 흰 패딩을 둘러 다크 모드에서도
 * 이물감이 없게 한다.
 */
export function QrCode({ value, size = 220, className = '' }) {
    const { modules, dim } = useMemo(() => {
        const r = encode(value, { ecc: ECC, border: BORDER })
        return { modules: r.data, dim: r.size }
    }, [value])

    // 어두운 모듈을 가로 방향으로 이어붙여 하나의 path 로 만든다.
    // 모듈마다 <rect> 를 찍으면 요소가 수백 개가 되는데, 런길이로 묶으면
    // 절반 이하로 줄어든다.
    const path = useMemo(() => {
        const parts = []
        for (let y = 0; y < dim; y++) {
            let x = 0
            while (x < dim) {
                if (!modules[y][x]) { x++; continue }
                let run = 1
                while (x + run < dim && modules[y][x + run]) run++
                parts.push(`M${x} ${y}h${run}v1h-${run}z`)
                x += run
            }
        }
        return parts.join('')
    }, [modules, dim])

    return (
        <svg
            viewBox={`0 0 ${dim} ${dim}`}
            width={size}
            height={size}
            shapeRendering="crispEdges"
            role="img"
            aria-label={value}
            className={className}
        >
            <rect width={dim} height={dim} fill="#ffffff" />
            <path d={path} fill="#000000" />
        </svg>
    )
}
