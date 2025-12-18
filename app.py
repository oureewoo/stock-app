import streamlit as st
import yfinance as yf
import pandas as pd

# --- 페이지 설정 ---
st.set_page_config(page_title="미국 주식 옵션 분석기", page_icon="📈")

# --- 제목 ---
st.title("🇺🇸 미국 주식 옵션 분석기")
st.write("티커를 입력하고 만기일을 선택하면, 세력들의 포지션을 분석해드립니다.")

# --- 1. 종목 입력 ---
ticker = st.text_input("종목 티커 입력 (예: QQQ, SPY, NVDA)", value="QQQ").upper()

if ticker:
    try:
        q = yf.Ticker(ticker)
        exps = q.options
        
        if not exps:
            st.error(f"❌ '{ticker}'의 옵션 데이터를 찾을 수 없습니다.")
        else:
            # --- 2. 만기일 선택 ---
            target_date = st.selectbox("만기일 선택 (Expiry Date)", exps)
            
            if st.button("분석 시작 🚀"):
                with st.spinner(f"'{ticker}' 데이터를 분석 중입니다..."):
                    # 데이터 가져오기
                    hist = q.history(period="1d")
                    current_price = hist['Close'].iloc[-1]
                    
                    opt = q.option_chain(target_date)
                    calls = opt.calls.fillna(0)
                    puts = opt.puts.fillna(0)

                    # --- Max Pain 계산 ---
                    all_strikes = sorted(list(set(calls['strike']) | set(puts['strike'])))
                    cash_values = []
                    for price in all_strikes:
                        call_cash = calls.apply(lambda x: max(0, price - x['strike']) * x['openInterest'], axis=1).sum()
                        put_cash = puts.apply(lambda x: max(0, x['strike'] - price) * x['openInterest'], axis=1).sum()
                        cash_values.append(call_cash + put_cash)
                    
                    min_cash_index = cash_values.index(min(cash_values))
                    max_pain = all_strikes[min_cash_index]

                    # --- Expected Move (EM) 계산 ---
                    df_strikes = pd.DataFrame({'strike': all_strikes})
                    closest_idx = (df_strikes['strike'] - current_price).abs().idxmin()
                    atm_strike = df_strikes.iloc[closest_idx]['strike']
                    
                    atm_call = calls[calls['strike'] == atm_strike]
                    atm_put = puts[puts['strike'] == atm_strike]
                    
                    atm_call_price = atm_call['lastPrice'].values[0] if not atm_call.empty else 0
                    atm_put_price = atm_put['lastPrice'].values[0] if not atm_put.empty else 0
                    
                    expected_move = atm_call_price + atm_put_price
                    em_percent = (expected_move / current_price) * 100
                    upper_bound = current_price + expected_move
                    lower_bound = current_price - expected_move

                    # --- 화면 출력 ---
                    st.success("분석 완료!")
                    
                    # 1. 주가 정보 표시
                    st.subheader(f"📊 {ticker} 현재가")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("현재 주가", f"${current_price:.2f}")
                    col2.metric("Max Pain", f"${max_pain}")
                    col3.metric("예상 변동폭(EM)", f"±{em_percent:.1f}%")

                    st.info(f"예상 범위: ${lower_bound:.2f} ~ ${upper_bound:.2f}")

                    # 2. 옵션 시장 현황
                    st.subheader("시장 심리 (Sentiment)")
                    
                    call_vol = calls['volume'].sum()
                    put_vol = puts['volume'].sum()
                    vol_pcr = put_vol / call_vol if call_vol > 0 else 0
                    
                    call_oi = calls['openInterest'].sum()
                    put_oi = puts['openInterest'].sum()
                    oi_pcr = put_oi / call_oi if call_oi > 0 else 0

                    col4, col5 = st.columns(2)
                    col4.metric("거래량 P/C Ratio", f"{vol_pcr:.2f}", delta_color="inverse")
                    col5.metric("미결제약정(OI) P/C Ratio", f"{oi_pcr:.2f}", delta_color="inverse")
                    st.caption("* P/C Ratio가 1.0 이상이면 하락(Put) 우세, 이하면 상승(Call) 우세")

                    # 3. Top 5 OI
                    st.subheader("🧱 큰손들의 벽 (Top 5 OI)")
                    
                    top_calls = calls.sort_values(by='openInterest', ascending=False).head(5)[['strike', 'openInterest', 'lastPrice']]
                    top_puts = puts.sort_values(by='openInterest', ascending=False).head(5)[['strike', 'openInterest', 'lastPrice']]
                    
                    col_call, col_put = st.columns(2)
                    
                    with col_call:
                        st.markdown("**🔴 저항선 (Call Top 5)**")
                        st.dataframe(top_calls.style.format({"strike": "${:.1f}", "openInterest": "{:,}", "lastPrice": "${:.2f}"}), hide_index=True)
                    
                    with col_put:
                        st.markdown("**🔵 지지선 (Put Top 5)**")
                        st.dataframe(top_puts.style.format({"strike": "${:.1f}", "openInterest": "{:,}", "lastPrice": "${:.2f}"}), hide_index=True)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
