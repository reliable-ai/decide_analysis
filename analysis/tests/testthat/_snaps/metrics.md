# decide produces expected results

    Code
      decide(mv, "accuracy")
    Output
      # A tibble: 3 x 6
        dimensions total_effect main_effect ratio_total_var ratio_main var_total
        <chr>             <dbl>       <dbl>           <dbl>      <dbl>     <dbl>
      1 mv_dim_A       0.00928     0.00926           0.793       0.998    0.0117
      2 mv_dim_B       0.00216     0.00214           0.184       0.992    0.0117
      3 mv_dim_C       0.000294    0.000264          0.0251      0.899    0.0117

