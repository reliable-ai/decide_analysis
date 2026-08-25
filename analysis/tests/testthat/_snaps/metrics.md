# decide produces expected results

    Code
      decide(mv, "accuracy")
    Output
      # A tibble: 3 x 5
        dimension decide_total decide_main ratio_main share_var_total
        <chr>            <dbl>       <dbl>      <dbl>           <dbl>
      1 mv_dim_A      0.00928     0.00926       0.998          0.793 
      2 mv_dim_B      0.00216     0.00214       0.992          0.184 
      3 mv_dim_C      0.000294    0.000264      0.899          0.0251

# decide produces expected results (when reporting all scores)

    Code
      decide(mv, "accuracy", report_all = TRUE)
    Output
      # A tibble: 3 x 8
        dimension decide_total decide_main decide_interactions ratio_main
        <chr>            <dbl>       <dbl>               <dbl>      <dbl>
      1 mv_dim_A      0.00928     0.00926             0.00926       0.998
      2 mv_dim_B      0.00216     0.00214             0.00214       0.992
      3 mv_dim_C      0.000294    0.000264            0.000264      0.899
      # i 3 more variables: ratio_interactions <dbl>, total_spread <dbl>,
      #   share_var_total <dbl>

